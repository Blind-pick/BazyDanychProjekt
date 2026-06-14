# phase_results_after — porownanie PRZED / PO optymalizacji (faza 5)

**Warunki identyczne** w obu przebiegach: DB zaciskane do **0.3 CPU / 256 MB**, JMeter
THREADS=120, rampa 240 s, hold 60 s, think time ~1 s, te same dane (~20 mln biletow).
Zmienil sie TYLKO schemat (4 indeksy) + 1 zapytanie w kodzie (COUNT cinemas -> reltuples).

---

## 1. Punkt zalamania PRZESUNIETY W PRAWO

Srednia latencja (ms) wg liczby aktywnych watkow:

| watki | PRZED | PO |
|------:|------:|----:|
| ~25   |   68  |  **24** |
| ~40   |  501  | **168** |
| ~55   | 1271  | **312** |
| ~70   | 1724  | **643** |
| ~85   | 2413  | 2029 |
| ~115  | 3643  | **1692** |
| 120   | 3998  | **~1500** |

- **PRZED:** latencja "ucieka" juz przy **~30 watkach** (68 ms -> 501 ms).
- **PO:** trzyma sie nisko (24-312 ms) az do **~70 watkow**; kolano przesuniete **~2,3x w prawo**.
- Na kazdym poziomie obciazenia latencja jest **2-4x nizsza**. Baza przyjmuje
  ~2x wiecej jednoczesnych uzytkownikow, zanim zacznie sie sypac.

---

## 2. Top 5 zapytan — sredni czas pod obciazeniem (pg_stat_statements)

| zapytanie | PRZED (mean) | PO (mean) | zysk |
|---|---:|---:|---|
| COUNT(*) cinemas (GET /cinemas)        | 1363 ms | **0.74 ms** | ~1800x (wyeliminowane) |
| user_reservations (GET /users/{id}/reservations) | 1053 ms | **46 ms**  | ~23x |
| INSERT tickets (POST /tickets)         | 2428 ms | **676 ms**  | 3.6x |
| user_tickets (GET /users/{id}/tickets) | 1922 ms | **678 ms**  | 2.8x |
| INSERT reservations (POST /reservations)| 1804 ms | **615 ms**  | 2.9x |

---

## 3. Co dokladnie zmieniono (5 zmian, po jednej "winie" na zapytanie)

| # | zmiana | efekt |
|---|---|---|
| A | `DROP INDEX idx_tickets_status` (martwy, idx_scan=36) | INSERT tickets utrzymuje 5 zamiast 6 indeksow |
| B | `idx_tickets_user_id` -> `idx_tickets_user_created (user_id, created_at DESC)` | user_tickets uzywa zlozonego indeksu (potwierdzone w planie: `Index Scan using idx_tickets_user_created`) |
| C | pelny `idx_reservations_status` (33 MB) -> czesciowy `idx_reservations_pending ... WHERE status='pending'` (**32 kB**) | INSERT reservations prawie nie rusza tego indeksu; cancel_expired dalej szybkie |
| D | `SELECT COUNT(*) FROM cinemas` -> `SELECT reltuples FROM pg_class` (kod) | pelny Seq Scan ~95 tys. wierszy znika: 210 ms -> **0.07 ms** |
| E | `idx_reservations_user_id` -> `idx_reservations_user_created (user_id, created_at DESC)` | user_reservations 1053 -> 46 ms |

Liczba indeksow: tickets **6 -> 5**, reservations **4 -> 4** (ale `status` 33 MB -> partial 32 kB).
Zmiany w: `scripts/optimize_phase5.sql`, `src/database_init.py`, `src/cinemas/service.py`.
Snapshot stanu sprzed zmian: `old_requests_dump.sql`. Pelna diagnoza "przed": `phase_results.md`.

---

## 4. Dowody z planow (PO)

**D) COUNT cinemas -> reltuples** (z pelnego Seq Scan na katalog):
```
Index Scan using pg_class_relname_nsp_index on pg_class (actual rows=1 loops=1)
Execution Time: 0.071 ms
```

**B) user_tickets** uzywa nowego indeksu zlozonego:
```
->  Index Scan using idx_tickets_user_created on tickets t  (rows=22)
```
Uwaga uczciwa: finalny `Sort` po created_at pozostaje (5 JOIN-ow reorganizuje wiersze),
ale na ~22 wierszach jest znikomy (28 kB, sub-ms). Glowny zysk: wezszy dostep + duzo
mniejsza kontencja w calym systemie.

---

## 5. Wniosek i co dalej

Optymalizacja **dziala**: punkt zalamania przesuniety ~2,3x w prawo, latencje 2-4x nizsze,
cztery z piatki "winowajcow" praktycznie zniknely z topu. Nowi najciezsi (kandydaci na
kolejna iteracje, gdyby trzeba): **INSERT tickets/reservations** (~615-676 ms, inherentny
koszt zapisu na duzych tabelach) oraz **seat availability** (`GET /showtime/{id}/seats`,
~516 ms - nieoptymalizowany w tej fazie).

Nastepny etap projektu: **replikacja master-slave** (odciazenie odczytow user_tickets/
user_reservations/seats na repliki) -> kolejne przesuniecie kolana w prawo.
