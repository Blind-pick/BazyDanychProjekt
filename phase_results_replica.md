# phase_results_replica — faza 7 (replikacja master-slave): wyniki i porownanie 3 faz

**Architektura po fazie 7:** master (zapisy) + replika/standby (odczyty), streaming replication.
API rozdziela ruch: `GET` (pool.acquire) -> **replika**, `POST/PATCH` (pool.transaction) -> **master**.
Oba wezly zaciskane po **0.3 CPU / 256 MB** (replika to OSOBNY wezel => DODAJE pojemnosc).
Test: ten sam profil co wczesniej (think time, 0.5 watku/s), THREADS do 120 / 200.

---

## 1. TABELA POROWNAWCZA — kolano vs liczba watkow (3 fazy)

Srednia latencja (ms) przy danej liczbie aktywnych watkow (im nizej, tym lepiej):

| watki | Faza 1: baseline | Faza 5: optymalizacja | Faza 7: replikacja |
|------:|-----------------:|----------------------:|-------------------:|
|  ~15  |        ~90       |          46           |       **22**       |
|  ~30  |         68       |          24           |       **14**       |
|  ~45  |       ~600       |         168           |       **22**       |
|  ~60  |       1271       |         312           |      **149**       |
|  ~75  |       ~1900      |         643           |      **333**       |
|  ~105 |       ~3300      |         749           |      **728**       |
|  ~120 |       3998       |        ~1500          |      **1123**      |

**KOLANO** (liczba watkow, przy ktorej latencja na stale przekracza ~0,5 s):

| | Faza 1 baseline | Faza 5 optymalizacja | Faza 7 replikacja |
|---|:---:|:---:|:---:|
| **kolano (~watkow)** | **~40** | **~70** | **~100** |

Kazda faza przesuwa kolano o ~30 watkow w prawo. Najwyrazniejszy zysk fazy 7 jest w
SRODKOWYM zakresie obciazenia (45-75 watkow): tam Faza 5 juz rosla, a Faza 7 trzyma sie
plasko (22-333 ms) - replika utrzymuje "region zapasu" mniej wiecej 2x dluzej.

---

## 2. ILU-KROTNIE SZYBCIEJ (uczciwie, per kategoria)

Najczystszy efekt to **odciazenie MASTERA z odczytow** => zapisy duzo szybsze
(porownanie srednich pod tym samym obciazeniem 120 watkow, Faza 5 vs Faza 7):

| zapytanie (zapis, master) | Faza 5 | Faza 7 | przyspieszenie |
|---|---:|---:|---|
| INSERT tickets        | 676 ms | **197 ms** | **3,4x** |
| INSERT reservations   | 615 ms | **134 ms** | **4,6x** |

Latencja CALEGO miksu w zakresie srednim (45-75 watkow): **2-10x nizsza** niz w Fazie 5
(np. przy 60 watkach 312 ms -> 149 ms; przy 45 watkach ~190 ms -> ~22 ms).

> **Wazna, uczciwa uwaga (i dobry wniosek do raportu):** replika to NIE darmowa pojemnosc
> odczytu. Standby musi **odtwarzac WAL** wszystkich zapisow mastera (a INSERT-y biletow/
> rezerwacji sa indeksowo ciezkie). Przy obciazeniu write-heavy proces odtwarzania zjada
> czesc 0.3 CPU repliki, wiec same CIEZKIE odczyty (user_tickets) na replice pod szczytem
> nie sa szybsze niz wczesniej na masterze. Zysk bierze sie z (a) odciazenia mastera =>
> szybkie zapisy, (b) rozlozenia ruchu na 2 wezly => kolano dalej w prawo, (c) szybkich
> lekkich odczytow. Replikacja pomaga najbardziej, gdy odczyty dominuja nad zapisami.

---

## 3. Najwazniejsze zapytania PO replikacji (gdzie teraz biegna)

**ODCZYTY -> replika** (pg_stat_statements repliki): user_tickets, user_reservations,
seat_availability, listy/PK-lookupy. Plany wykonania IDENTYCZNE jak na masterze - indeksy
z fazy 5 (idx_tickets_user_created itd.) sa replikowane streamingiem, wiec replika korzysta
z tych samych optymalizacji.

**ZAPISY -> master** (pg_stat_statements mastera): INSERT tickets/reservations, sprawdzenia
unikalnosci, cancel_expired. Master nie obsluguje juz odczytow => zapisy ~3-5x szybsze.

---

## 4. Grafana

Widoczne na dashboardzie **"Punkt zalamania"** (http://localhost:3000): panele p95 per
endpoint i req/s-vs-p95 pokazuja te sama krzywa co tabela wyzej - w Fazie 7 latencja trzyma
sie nisko do wiekszej liczby watkow, a kolano jest dalej w prawo. CPU obu wezlow (master i
replika) zbiera cadvisor (kontenery cinema_db i cinema_db_replica).

---

## 5. Wniosek

Trzy fazy, monotoniczna poprawa - kolano: **~40 -> ~70 -> ~100 watkow**. Replikacja:
- odciaza master => **zapisy 3-5x szybsze**,
- rozklada ruch na 2 wezly => **kolano ~1,4x dalej** niz po samej optymalizacji,
- najwiekszy zysk w srodkowym zakresie obciazenia.
Ograniczenie: standby odtwarza WAL zapisow, wiec pod write-heavy szczytem nie jest to
pelne podwojenie pojemnosci odczytu - ale net pozostaje wyraznie dodatni.
