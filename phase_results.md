# phase_results — diagnostyka 5 najciezszych zapytan

**Wygenerowano:** 2026-06-14 14:46  |  baza: kino (zaciskana do testu)  |  user_id=933616

Top 5 wybrane wg `mean_exec_time` (pg_stat_statements, po ostatnim przebiegu obciazeniowym).
EXPLAIN biegnie POJEDYNCZO (~10-210 ms); pod OBCIAZENIEM te zapytania sa 10-40x wolniejsze
(`mean_ms` w rankingu) przez wypieranie cache 256MB + glod CPU. EXPLAIN mowi GDZIE jest praca.

## Ranking (pg_stat_statements)
```
WARNING:  database "kino" has no actual collation version, but a version was recorded
 mean_ms | max_ms | calls | pct_total | cache_hit_pct |                        zapytanie                        
---------+--------+-------+-----------+---------------+---------------------------------------------------------
  2427.9 |  13198 |    74 |       2.1 |          83.9 | INSERT INTO tickets (showtime_id, seat_id, user_id, fin
  2247.4 |  25400 |   397 |      10.2 |          84.1 | INSERT INTO tickets (showtime_id, seat_id, user_id, fin
  1921.9 |  10504 |   620 |      13.6 |          64.4 | SELECT t.ticket_id, t.showtime_id, t.seat_id, t.status,
  1829.0 |  12688 |    80 |       1.7 |          85.5 | INSERT INTO tickets (showtime_id, seat_id, user_id, fin
  1804.5 |  21212 |   484 |      10.0 |          80.0 | INSERT INTO reservations (user_id, showtime_id, status)
  1763.1 |  13703 |   100 |       2.0 |          79.7 | INSERT INTO reservations (user_id, showtime_id, status)
  1408.4 |  10405 |    21 |       0.3 |          87.9 | INSERT INTO tickets (showtime_id, seat_id, user_id, fin
  1363.2 |   7200 |   671 |      10.5 |          99.3 | SELECT COUNT(*) FROM cinemas
(8 rows)

```

## A) INSERT do tickets — POST /tickets

**1. Zapytanie**

```sql
INSERT INTO tickets (showtime_id, seat_id, user_id, final_price, status, reservation_id) VALUES (166836, 135301, 383010, 25.00, 'valid', NULL)
```

**2. EXPLAIN — komenda i zwrotka**

```
-- w transakcji + ROLLBACK (bez zmian w danych):
BEGIN;
EXPLAIN (ANALYZE, BUFFERS) INSERT INTO tickets (showtime_id, seat_id, user_id, final_price, status, reservation_id) VALUES (166836, 135301, 383010, 25.00, 'valid', NULL);
ROLLBACK;

-- zwrotka:
WARNING:  database "kino" has no actual collation version, but a version was recorded
BEGIN
                                           QUERY PLAN                                            
-------------------------------------------------------------------------------------------------
 Insert on tickets  (cost=0.00..0.02 rows=0 width=0) (actual time=12.575..12.576 rows=0 loops=1)
   Buffers: shared hit=127 read=8 dirtied=8
   ->  Result  (cost=0.00..0.02 rows=1 width=56) (actual time=0.160..0.161 rows=1 loops=1)
         Buffers: shared hit=13 dirtied=1
 Planning:
   Buffers: shared hit=15
 Planning Time: 0.204 ms
 Trigger for constraint tickets_showtime_id_fkey: time=1.426 calls=1
 Trigger for constraint tickets_seat_id_fkey: time=61.328 calls=1
 Trigger for constraint tickets_user_id_fkey: time=2.457 calls=1
 Trigger for constraint tickets_reservation_id_fkey: time=0.138 calls=1
 Trigger for constraint tickets_ticket_group_id_fkey: time=0.081 calls=1
 Trigger for constraint tickets_promotion_id_fkey: time=0.100 calls=1
 Execution Time: 78.175 ms
(14 rows)

ROLLBACK
```

**3. Wnioski**

- Sam zapis wiersza jest tani; koszt to utrzymanie **6 indeksow** tabeli tickets (~1.4 GB: pkey 429MB, unique_ticket_per_seat_showtime 429MB, idx_user_id 152MB, idx_seat_id 135MB, idx_showtime_id 135MB, idx_status 132MB) + **6 triggerow FK** (widoczne w planie: showtime/seat/user/...).
- Pod obciazeniem najdrozszy zapis (top1 mean ~2.4 s): kazdy INSERT dotyka lisciowych stron 6 indeksow rozsianych po 1.4 GB => losowe zapisy + presja na cache.
- W tabeli kontekstowej `idx_tickets_status` ma idx_scan=36 — praktycznie NIEUZYWANY w SELECT, a placimy za jego utrzymanie przy kazdym insercie.

**4. Propozycja naprawy**

**DROP INDEX idx_tickets_status;** — usuwa 1 z 6 aktualizacji indeksu na kazdym INSERT (~-17% pracy indeksow), nie tracimy nic w odczytach (status i tak filtrujemy rzadko). Lzejszy zapis => prog zalamania dalej w prawo.

## B) SELECT user_tickets — GET /users/{id}/tickets (5 JOIN)

**1. Zapytanie**

```sql
SELECT t.ticket_id, t.showtime_id, t.seat_id, t.status, t.final_price, m.title, s.start_datetime, c.name, se.row_label, se.seat_number, t.created_at FROM tickets t JOIN showtimes s ON t.showtime_id=s.showtime_id JOIN movies m ON s.movie_id=m.movie_id JOIN halls h ON s.hall_id=h.hall_id JOIN cinemas c ON h.cinema_id=c.cinema_id JOIN seats se ON t.seat_id=se.seat_id WHERE t.user_id=933616 ORDER BY t.created_at DESC OFFSET 0 LIMIT 20
```

**2. EXPLAIN — komenda i zwrotka**

```
EXPLAIN (ANALYZE, BUFFERS)
SELECT t.ticket_id, t.showtime_id, t.seat_id, t.status, t.final_price, m.title, s.start_datetime, c.name, se.row_label, se.seat_number, t.created_at FROM tickets t JOIN showtimes s ON t.showtime_id=s.showtime_id JOIN movies m ON s.movie_id=m.movie_id JOIN halls h ON s.hall_id=h.hall_id JOIN cinemas c ON h.cinema_id=c.cinema_id JOIN seats se ON t.seat_id=se.seat_id WHERE t.user_id=933616 ORDER BY t.created_at DESC OFFSET 0 LIMIT 20;

-- zwrotka:
WARNING:  database "kino" has no actual collation version, but a version was recorded
                                                                                          QUERY PLAN                                                                                           
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 Limit  (cost=473.09..473.14 rows=20 width=112) (actual time=2.969..2.986 rows=20 loops=1)
   Buffers: shared hit=223
   ->  Sort  (cost=473.09..473.14 rows=20 width=112) (actual time=2.966..2.977 rows=20 loops=1)
         Sort Key: t.created_at DESC
         Sort Method: quicksort  Memory: 28kB
         Buffers: shared hit=223
         ->  Nested Loop  (cost=282.37..472.65 rows=20 width=112) (actual time=1.781..2.829 rows=22 loops=1)
               Buffers: shared hit=220
               ->  Hash Join  (cost=281.95..303.90 rows=20 width=108) (actual time=1.728..2.327 rows=22 loops=1)
                     Hash Cond: (m.movie_id = s.movie_id)
                     Buffers: shared hit=132
                     ->  Seq Scan on movies m  (cost=0.00..18.00 rows=1000 width=19) (actual time=0.019..0.271 rows=1000 loops=1)
                           Buffers: shared hit=8
                     ->  Hash  (cost=281.70..281.70 rows=20 width=97) (actual time=1.640..1.645 rows=22 loops=1)
                           Buckets: 1024  Batches: 1  Memory Usage: 10kB
                           Buffers: shared hit=124
                           ->  Merge Join  (cost=276.47..281.70 rows=20 width=97) (actual time=1.518..1.586 rows=22 loops=1)
                                 Merge Cond: (c.cinema_id = h.cinema_id)
                                 Buffers: shared hit=124
                                 ->  Index Scan using cinemas_pkey on cinemas c  (cost=0.29..8236.90 rows=108336 width=60) (actual time=0.042..0.069 rows=48 loops=1)
                                       Buffers: shared hit=3
                                 ->  Sort  (cost=276.16..276.21 rows=20 width=45) (actual time=1.454..1.462 rows=22 loops=1)
                                       Sort Key: h.cinema_id
                                       Sort Method: quicksort  Memory: 26kB
                                       Buffers: shared hit=121
                                       ->  Hash Join  (cost=253.78..275.73 rows=20 width=45) (actual time=0.885..1.373 rows=22 loops=1)
                                             Hash Cond: (h.hall_id = s.hall_id)
                                             Buffers: shared hit=121
                                             ->  Seq Scan on halls h  (cost=0.00..18.00 rows=1000 width=8) (actual time=0.013..0.283 rows=1000 loops=1)
                                                   Buffers: shared hit=8
                                             ->  Hash  (cost=253.53..253.53 rows=20 width=45) (actual time=0.700..0.702 rows=22 loops=1)
                                                   Buckets: 1024  Batches: 1  Memory Usage: 10kB
                                                   Buffers: shared hit=113
                                                   ->  Nested Loop  (cost=0.86..253.53 rows=20 width=45) (actual time=0.103..0.640 rows=22 loops=1)
                                                         Buffers: shared hit=113
                                                         ->  Index Scan using idx_tickets_user_id on tickets t  (cost=0.44..84.78 rows=20 width=29) (actual time=0.059..0.222 rows=22 loops=1)
                                                               Index Cond: (user_id = 933616)
                                                               Buffers: shared hit=25
                                                         ->  Index Scan using showtimes_pkey on showtimes s  (cost=0.42..8.44 rows=1 width=20) (actual time=0.017..0.017 rows=1 loops=22)
                                                               Index Cond: (showtime_id = t.showtime_id)
                                                               Buffers: shared hit=88
               ->  Index Scan using seats_pkey on seats se  (cost=0.42..8.44 rows=1 width=8) (actual time=0.021..0.021 rows=1 loops=22)
                     Index Cond: (seat_id = t.seat_id)
                     Buffers: shared hit=88
 Planning:
   Buffers: shared hit=644
 Planning Time: 86.872 ms
 Execution Time: 4.105 ms
(48 rows)

```

**3. Wnioski**

- Plan uzywa `idx_tickets_user_id` (dobrze), ale dla biletow usera robi losowe lookupy PK do showtimes/seats => **najwiecej stron z dysku (read~79/call) i najnizszy cache hit ~64%** z calej piatki. To ono najmocniej bije w I/O pod presja.
- `ORDER BY created_at DESC` wymusza osobny wezel **Sort** — indeks po user_id nie zna kolejnosci czasowej, wiec pobiera WSZYSTKIE bilety usera i sortuje, dopiero potem LIMIT 20.

**4. Propozycja naprawy**

**CREATE INDEX ON tickets (user_id, created_at DESC);** — eliminuje Sort i pozwala pobrac od razu 20 najnowszych biletow usera bez czytania reszty (mniej losowych odczytow, znika sortowanie).

## C) INSERT do reservations — POST /reservations

**1. Zapytanie**

```sql
INSERT INTO reservations (user_id, showtime_id, status) VALUES (383010, 166836, 'pending')
```

**2. EXPLAIN — komenda i zwrotka**

```
-- w transakcji + ROLLBACK (bez zmian w danych):
BEGIN;
EXPLAIN (ANALYZE, BUFFERS) INSERT INTO reservations (user_id, showtime_id, status) VALUES (383010, 166836, 'pending');
ROLLBACK;

-- zwrotka:
WARNING:  database "kino" has no actual collation version, but a version was recorded
BEGIN
                                             QUERY PLAN                                             
----------------------------------------------------------------------------------------------------
 Insert on reservations  (cost=0.00..0.02 rows=0 width=0) (actual time=6.359..6.359 rows=0 loops=1)
   Buffers: shared hit=98 read=4 dirtied=6
   ->  Result  (cost=0.00..0.02 rows=1 width=24) (actual time=0.146..0.147 rows=1 loops=1)
         Buffers: shared hit=13 dirtied=1
 Planning:
   Buffers: shared hit=19
 Planning Time: 0.177 ms
 Trigger for constraint reservations_user_id_fkey: time=1.515 calls=1
 Trigger for constraint reservations_showtime_id_fkey: time=0.884 calls=1
 Execution Time: 8.837 ms
(10 rows)

ROLLBACK
```

**3. Wnioski**

- Koszt = utrzymanie **4 indeksow** (pkey 107MB, user_id 56MB, showtime_id 37MB, status 33MB) + 2 triggery FK.
- `idx_reservations_status` (kolumna o 3 wartosciach, 33 MB nad 5 mln wierszy) jest aktualizowany przy KAZDYM insercie, a w praktyce sluzy tylko zapytaniu cancel_expired (status='pending', rzadkie). Pelny indeks po malo selektywnej kolumnie to marny zwrot.

**4. Propozycja naprawy**

**Zamien pelny indeks na CZESCIOWY:** `DROP INDEX idx_reservations_status; CREATE INDEX ON reservations (created_at) WHERE status='pending';` — indeks kurczy sie z 33 MB do ~KB (tylko wiersze pending), wiec INSERT prawie go nie rusza, a cancel_expired dalej ma szybki dostep. Lzejszy zapis + szybsze sprzatanie.

## D) SELECT COUNT(*) FROM cinemas — GET /cinemas

**1. Zapytanie**

```sql
SELECT COUNT(*) FROM cinemas
```

**2. EXPLAIN — komenda i zwrotka**

```
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) FROM cinemas;

-- zwrotka:
WARNING:  database "kino" has no actual collation version, but a version was recorded
                                                    QUERY PLAN                                                     
-------------------------------------------------------------------------------------------------------------------
 Aggregate  (cost=2883.20..2883.21 rows=1 width=8) (actual time=12.231..12.232 rows=1 loops=1)
   Buffers: shared hit=1529
   ->  Seq Scan on cinemas  (cost=0.00..2612.36 rows=108336 width=0) (actual time=0.011..7.195 rows=94677 loops=1)
         Buffers: shared hit=1529
 Planning:
   Buffers: shared hit=85
 Planning Time: 0.639 ms
 Execution Time: 12.357 ms
(8 rows)

```

**3. Wnioski**

- **Pelny Seq Scan ~95 tys. wierszy (1529 stron)** przy KAZDEJ liscie kin, tylko po to, by zwrocic `total` do paginacji.
- Cache hit ~99% (tabela miesci sie w cache), wiec to koszt **CPU** (skan + zliczanie) — pod glodem CPU (0.3 rdzenia) 210 ms rosnie do ~1.4 s i to jest ~10% calego czasu bazy.

**4. Propozycja naprawy**

**Nie liczyc dokladnego total co request:** uzyc szacunku z katalogu `SELECT reltuples::bigint FROM pg_class WHERE relname='cinemas'` (stala, ~0 ms) albo usunac `total` z odpowiedzi. Pelny skan znika z kazdego GET /cinemas.

## E) SELECT user_reservations — GET /users/{id}/reservations (4 JOIN)

**1. Zapytanie**

```sql
SELECT r.reservation_id, r.showtime_id, r.status, r.created_at, m.title, s.start_datetime, c.name, c.city FROM reservations r JOIN showtimes s ON r.showtime_id=s.showtime_id JOIN movies m ON s.movie_id=m.movie_id JOIN halls h ON s.hall_id=h.hall_id JOIN cinemas c ON h.cinema_id=c.cinema_id WHERE r.user_id=933616 ORDER BY r.created_at DESC OFFSET 0 LIMIT 20
```

**2. EXPLAIN — komenda i zwrotka**

```
EXPLAIN (ANALYZE, BUFFERS)
SELECT r.reservation_id, r.showtime_id, r.status, r.created_at, m.title, s.start_datetime, c.name, c.city FROM reservations r JOIN showtimes s ON r.showtime_id=s.showtime_id JOIN movies m ON s.movie_id=m.movie_id JOIN halls h ON s.hall_id=h.hall_id JOIN cinemas c ON h.cinema_id=c.cinema_id WHERE r.user_id=933616 ORDER BY r.created_at DESC OFFSET 0 LIMIT 20;

-- zwrotka:
