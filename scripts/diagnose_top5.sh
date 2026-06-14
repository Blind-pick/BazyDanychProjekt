#!/usr/bin/env bash

set -euo pipefail
cd "$(dirname "$0")/.."

OUT="${1:-phase_results.md}"
DB="docker exec cinema_db psql -U postgres -d kino -X"
emit() { printf '%s\n' "$@" >> "$OUT"; }

U_ID=$($DB -tAc "SELECT user_id FROM tickets LIMIT 1" | tr -dc '0-9')
S_ID=$($DB -tAc "SELECT (random()*199999+1)::int")
SEAT=$($DB -tAc "SELECT (random()*199999+1)::int")
W_USER=$($DB -tAc "SELECT (random()*1100000+1)::int")

Q_INS_TICKET="INSERT INTO tickets (showtime_id, seat_id, user_id, final_price, status, reservation_id) VALUES ($S_ID, $SEAT, $W_USER, 25.00, 'valid', NULL)"
Q_UTICKETS="SELECT t.ticket_id, t.showtime_id, t.seat_id, t.status, t.final_price, m.title, s.start_datetime, c.name, se.row_label, se.seat_number, t.created_at FROM tickets t JOIN showtimes s ON t.showtime_id=s.showtime_id JOIN movies m ON s.movie_id=m.movie_id JOIN halls h ON s.hall_id=h.hall_id JOIN cinemas c ON h.cinema_id=c.cinema_id JOIN seats se ON t.seat_id=se.seat_id WHERE t.user_id=$U_ID ORDER BY t.created_at DESC OFFSET 0 LIMIT 20"
Q_INS_RESV="INSERT INTO reservations (user_id, showtime_id, status) VALUES ($W_USER, $S_ID, 'pending')"
Q_COUNT="SELECT COUNT(*) FROM cinemas"
Q_URESV="SELECT r.reservation_id, r.showtime_id, r.status, r.created_at, m.title, s.start_datetime, c.name, c.city FROM reservations r JOIN showtimes s ON r.showtime_id=s.showtime_id JOIN movies m ON s.movie_id=m.movie_id JOIN halls h ON s.hall_id=h.hall_id JOIN cinemas c ON h.cinema_id=c.cinema_id WHERE r.user_id=$U_ID ORDER BY r.created_at DESC OFFSET 0 LIMIT 20"

: > "$OUT"
emit "# phase_results — diagnostyka 5 najciezszych zapytan" \
     "" \
     "**Wygenerowano:** $(date '+%Y-%m-%d %H:%M')  |  baza: kino (zaciskana do testu)  |  user_id=$U_ID" \
     "" \
     "Top 5 wybrane wg \`mean_exec_time\` (pg_stat_statements, po ostatnim przebiegu obciazeniowym)." \
     "EXPLAIN biegnie POJEDYNCZO (~10-210 ms); pod OBCIAZENIEM te zapytania sa 10-40x wolniejsze" \
     "(\`mean_ms\` w rankingu) przez wypieranie cache 256MB + glod CPU. EXPLAIN mowi GDZIE jest praca." \
     "" \
     "## Ranking (pg_stat_statements)" \
     '```'
$DB -c "
SELECT round(mean_exec_time::numeric,1) AS mean_ms, round(max_exec_time::numeric,0) AS max_ms, calls,
       round((100*total_exec_time/sum(total_exec_time) OVER())::numeric,1) AS pct_total,
       round(100*shared_blks_hit::numeric/nullif(shared_blks_hit+shared_blks_read,0),1) AS cache_hit_pct,
       left(regexp_replace(query,'\s+',' ','g'),55) AS zapytanie
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat%' AND query !~* 'information_schema|pg_catalog|EXPLAIN' AND calls > 20
ORDER BY mean_exec_time DESC LIMIT 8;" >> "$OUT" 2>&1
emit '```'

section() {  # $1=naglowek  $2=sql  $3=is_insert(0/1)  $4=wnioski  $5=propozycja
  emit "" "## $1" "" "**1. Zapytanie**" "" '```sql' "$2" '```' \
       "" "**2. EXPLAIN — komenda i zwrotka**" "" '```'
  if [ "$3" = "1" ]; then
    emit "-- w transakcji + ROLLBACK (bez zmian w danych):" "BEGIN;" "EXPLAIN (ANALYZE, BUFFERS) $2;" "ROLLBACK;" "" "-- zwrotka:"
    $DB -c "BEGIN; EXPLAIN (ANALYZE, BUFFERS) $2; ROLLBACK;" >> "$OUT" 2>&1
  else
    emit "EXPLAIN (ANALYZE, BUFFERS)" "$2;" "" "-- zwrotka:"
    $DB -c "EXPLAIN (ANALYZE, BUFFERS) $2" >> "$OUT" 2>&1
  fi
  emit '```' "" "**3. Wnioski**" "" "$4" "" "**4. Propozycja naprawy**" "" "$5"
}

section "A) INSERT do tickets — POST /tickets" "$Q_INS_TICKET" 1 \
"- Sam zapis wiersza jest tani; koszt to utrzymanie **6 indeksow** tabeli tickets (~1.4 GB: pkey 429MB, unique_ticket_per_seat_showtime 429MB, idx_user_id 152MB, idx_seat_id 135MB, idx_showtime_id 135MB, idx_status 132MB) + **6 triggerow FK** (widoczne w planie: showtime/seat/user/...).
- Pod obciazeniem najdrozszy zapis (top1 mean ~2.4 s): kazdy INSERT dotyka lisciowych stron 6 indeksow rozsianych po 1.4 GB => losowe zapisy + presja na cache.
- W tabeli kontekstowej \`idx_tickets_status\` ma idx_scan=36 — praktycznie NIEUZYWANY w SELECT, a placimy za jego utrzymanie przy kazdym insercie." \
"**DROP INDEX idx_tickets_status;** — usuwa 1 z 6 aktualizacji indeksu na kazdym INSERT (~-17% pracy indeksow), nie tracimy nic w odczytach (status i tak filtrujemy rzadko). Lzejszy zapis => prog zalamania dalej w prawo."

section "B) SELECT user_tickets — GET /users/{id}/tickets (5 JOIN)" "$Q_UTICKETS" 0 \
"- Plan uzywa \`idx_tickets_user_id\` (dobrze), ale dla biletow usera robi losowe lookupy PK do showtimes/seats => **najwiecej stron z dysku (read~79/call) i najnizszy cache hit ~64%** z calej piatki. To ono najmocniej bije w I/O pod presja.
- \`ORDER BY created_at DESC\` wymusza osobny wezel **Sort** — indeks po user_id nie zna kolejnosci czasowej, wiec pobiera WSZYSTKIE bilety usera i sortuje, dopiero potem LIMIT 20." \
"**CREATE INDEX ON tickets (user_id, created_at DESC);** — eliminuje Sort i pozwala pobrac od razu 20 najnowszych biletow usera bez czytania reszty (mniej losowych odczytow, znika sortowanie)."

section "C) INSERT do reservations — POST /reservations" "$Q_INS_RESV" 1 \
"- Koszt = utrzymanie **4 indeksow** (pkey 107MB, user_id 56MB, showtime_id 37MB, status 33MB) + 2 triggery FK.
- \`idx_reservations_status\` (kolumna o 3 wartosciach, 33 MB nad 5 mln wierszy) jest aktualizowany przy KAZDYM insercie, a w praktyce sluzy tylko zapytaniu cancel_expired (status='pending', rzadkie). Pelny indeks po malo selektywnej kolumnie to marny zwrot." \
"**Zamien pelny indeks na CZESCIOWY:** \`DROP INDEX idx_reservations_status; CREATE INDEX ON reservations (created_at) WHERE status='pending';\` — indeks kurczy sie z 33 MB do ~KB (tylko wiersze pending), wiec INSERT prawie go nie rusza, a cancel_expired dalej ma szybki dostep. Lzejszy zapis + szybsze sprzatanie."

section "D) SELECT COUNT(*) FROM cinemas — GET /cinemas" "$Q_COUNT" 0 \
"- **Pelny Seq Scan ~95 tys. wierszy (1529 stron)** przy KAZDEJ liscie kin, tylko po to, by zwrocic \`total\` do paginacji.
- Cache hit ~99% (tabela miesci sie w cache), wiec to koszt **CPU** (skan + zliczanie) — pod glodem CPU (0.3 rdzenia) 210 ms rosnie do ~1.4 s i to jest ~10% calego czasu bazy." \
"**Nie liczyc dokladnego total co request:** uzyc szacunku z katalogu \`SELECT reltuples::bigint FROM pg_class WHERE relname='cinemas'\` (stala, ~0 ms) albo usunac \`total\` z odpowiedzi. Pelny skan znika z kazdego GET /cinemas."

section "E) SELECT user_reservations — GET /users/{id}/reservations (4 JOIN)" "$Q_URESV" 0 \
"- \`idx_reservations_user_id\` uzyty, ale sam Index Scan to ~70 ms (losowe odczyty do reservations + PK lookupy showtimes).
- Znowu **Sort** po \`created_at DESC\` — ten sam wzorzec co user_tickets." \
"**CREATE INDEX ON reservations (user_id, created_at DESC);** — eliminuje Sort i ogranicza skan do najnowszych rezerwacji usera (mniej losowych odczytow)."

echo "Gotowe -> $OUT"
