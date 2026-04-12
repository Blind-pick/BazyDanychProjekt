# INSTRUKCJE URUCHOMIENIA - Art Cinema Reservation API v2.0

## Szybki Start (Docker - Rekomendowany)

### Wymagania:
- Docker & Docker Compose zainstalowane
- Port 8000 i 5432 dostępne

### Kroki:
```bash
cd BazyDanychProjekt

# 1. Uruchom cały stack (baza + API)
docker-compose up --build

# Output powinien pokazać:
# [OK] db_1 is now ready to accept connections
# [OK] api_1 has started successfully
# [OK] Uvicorn running on http://0.0.0.0:8000
```

API będzie dostępny: **http://127.0.0.1:8000**

---

## 📚 Podstawowe Operacje

### 1. Rejestracja Użytkownika
```bash
curl -X POST http://127.0.0.1:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "anna@example.com",
    "username": "anna_smith"
  }'
```
**Odpowiedź:** `{"user_id": 1, "email": "anna@example.com", ...}`

---

### 2. Utwórz Kino
```bash
curl -X POST http://127.0.0.1:8000/api/v1/cinemas \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cinema City",
    "city": "Warszawa"
  }'
```
**Odpowiedź:** `{"cinema_id": 1, "name": "Cinema City", ...}`

---

### 3. Pobierz Dostępne Miejsca na Seans
```bash
curl http://127.0.0.1:8000/api/v1/tickets/showtime/1/seats
```
**Odpowiedź:** Lista miejsc z dostępnością i cenami
```json
[
  {
    "seat_id": 1,
    "row_label": "A",
    "seat_number": 1,
    "seat_type": "Standard",
    "is_available": true,
    "base_price": "29.99"
  },
  ...
]
```

---

### 4. Zrób Rezerwację
```bash
curl -X POST http://127.0.0.1:8000/api/v1/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "showtime_id": 1,
    "seat_ids": [1, 2, 3]
  }'
```
**Odpowiedź:** `{"reservation_id": 1, "status": "pending", ...}`

> **Ważne**: Rezerwacja wygasa po 15 minutach jeżeli nie zostanie potwierdzona!

---

### 5. Potwierdź Rezerwację
```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/reservations/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}'
```

---

### 6. Utwórz Bilet
```bash
curl -X POST http://127.0.0.1:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "showtime_id": 1,
    "seat_id": 1,
    "user_id": 1,
    "final_price": 29.99,
    "status": "valid",
    "reservation_id": 1
  }'
```

---

### 7. Utwórz Płatność
```bash
curl -X POST http://127.0.0.1:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "payment_method_id": 1,
    "amount": 29.99,
    "status": "pending",
    "ticket_ids": [1]
  }'
```

---

### 8. Oznacz Płatność jako Wykonaną
```bash
curl -X POST http://127.0.0.1:8000/api/v1/payments/1/complete
```

---

## Interaktywny Test CLI

Zamiast ręcznych curl-ów, użyj interaktywnego CLI:

```bash
# 1. Załaduj dane testowe (opcjonalnie)
python scripts/load_sample_data.py

# 2. Uruchom interaktywny client
python scripts/test_api.py

# Możliwe komendy w CLI:
#   1. register         - Rejestracja użytkownika
#   2. user_tickets     - Pobierz bilety użytkownika
#   3. user_reservations - Pobierz rezerwacje
#   4. create_cinema    - Utwórz kino
#   5. list_cinemas     - Wyświetl kina
#   6. create_reservation - Zrób rezerwację
#   7. get_seats        - Dostępne miejsca
#   8. create_payment   - Utwórz płatność
#   9. session          - Stan sesji
#   10. health          - Health check
#   11. help            - Pomoc
#   0. exit             - Wyjście
```

---

## 📊 Dostępne Endpointy - Pełny List

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/health` | Health check |
| GET | `/api/v1/cinemas` | Lista kin |
| POST | `/api/v1/cinemas` | Utwórz kino |
| GET | `/api/v1/cinemas/{id}` | Szczegóły kina |
| POST | `/api/v1/users` | Rejestracja |
| GET | `/api/v1/users/{id}` | Szczegóły użytkownika |
| GET | `/api/v1/users/{id}/tickets` | Bilety użytkownika |
| GET | `/api/v1/users/{id}/reservations` | Rezerwacje użytkownika |
| POST | `/api/v1/reservations` | Nowa rezerwacja |
| GET | `/api/v1/reservations/{id}` | Szczegóły rezerwacji |
| PATCH | `/api/v1/reservations/{id}/status` | Zmień status |
| DELETE | `/api/v1/reservations/{id}` | Anuluj rezerwację |
| GET | `/api/v1/tickets/showtime/{id}/seats` | Miejsca na seans |
| POST | `/api/v1/tickets` | Nowy bilet |
| GET | `/api/v1/tickets/{id}` | Szczegóły biletu |
| POST | `/api/v1/payments` | Nowa płatność |
| GET | `/api/v1/payments/{id}` | Szczegóły płatności |
| POST | `/api/v1/payments/{id}/complete` | Potwierdź płatność |

---

## Lokalna Instalacja (bez Docker)

Jeśli chcesz nie używać Docker-a:

### 1. PostgreSQL
```bash
# macOS
brew install postgresql@15

# Ubuntu
sudo apt-get install postgresql-15

# Windows
# Pobierz https://www.postgresql.org/download/windows/

# Uruchom serwer
brew services start postgresql@15
```

### 2. Python Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# lub
venv\Scripts\activate  # Windows
```

### 3. Zainstaluj Dependencies
```bash
pip install -r requirements.txt
```

### 4. Konfiguracja Bazy
```bash
# Utwórz bazę
createdb kino

# lub użyj psql
psql -c "CREATE DATABASE kino;"
```

### 5. Set Environment Variables
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=kino
export DB_USER=postgres
export DB_PASSWORD=<twoje_hasło>
export ENVIRONMENT=local
```

### 6. Uruchom API
```bash
uvicorn src.main:app --reload --port 8000
```

API dostępne pod: **http://localhost:8000**

---

## 📖 Dokumentacja API

### OpenAPI/Swagger (tylko w development mode)
```
http://127.0.0.1:8000/docs
```

Tam możesz:
- ✅ Wyświetlić wszystkie endpointy
- ✅ Przeczytać opisy i wymagane pola
- ✅ Testować żądania bezpośrednio z przeglądarki
- ✅ Zobaczyć przykładowe odpowiedzi

---

## 🔒 Transakcje i Bezpieczeństwo

Projekt implementuje zaawansowane mechanizmy bazy danych:

- **ACID Transactions**: Każda operacja jest atomowa
- **REPEATABLE_READ Isolation**: Zapobiega konfliktom konkurencyjnym
- **Connection Pooling**: 5-20 połączeń, skalowalne
- **Constraint-based Integrity**: Unique, FK, CHECK constraints
- **Auto-Rollback**: Exception → rollback transakcji

**Przykład**: Rezerwacja jest bezpieczna nawet przy wielu użytkownikach rezerwujących jednocześnie.

---

## 📊 Struktura Bazy

```
cinemas (id, name, city)
  ├── halls (id, cinema_id, name, capacity)
  │   └── seats (id, hall_id, row, seat_number)
  └── showtimes (id, movie_id, hall_id, start_time, price)
        ├── tickets (id, showtime_id, seat_id, user_id, price, status)
        │   └── payments (id, amount, method, status)
        └── reservations (id, user_id, showtime_id, status)
            └── reservation_seats (reservation_id, seat_id)

users (id, email, username)
  ├── tickets (id, user_id, showtime_id, ...)
  ├── reservations (id, user_id, showtime_id, ...)
  └── payments (id, user_id, method_id, ...)
```

---

## 🐛 Troubleshooting

### "Connection refused" na port 5432
```bash
# Sprawdź czy PostgreSQL działa
sudo systemctl status postgresql

# Lub kliknij Docker Dashboard i uruchom db w docker-compose
docker-compose up db
```

### "Database 'kino' does not exist"
```bash
# Kontener API automatycznie tworzy bazę
# Ale jeśli problem, utwórz ręcznie:
psql -U postgres -c "CREATE DATABASE kino;"
```

### "API response timeout"
- Sprawdź czy baza jest gotowa: `curl http://127.0.0.1:5432`
- Sprawdź logi: `docker-compose logs api`
- Resetuj: `docker-compose down -v` i `docker-compose up --build`

---

## 📞 Informacje Przydatne

**Baza danych:**
- Host: `localhost` (dev) lub `db` (docker)
- Port: 5432
- Database: `kino`
- User: `postgres`

**API:**
- Base URL: `http://127.0.0.1:8000`
- API Prefix: `/api/v1`
- Docs: `/docs` (dev), `/redoc` (dev)
- Health: `/health` (zawsze)

**Test Data:**
- Automatic seed na startup
- Albo: `python scripts/load_sample_data.py`

---

## ✅ Checklist Sprawdzenia

Po uruchomieniu:
- [ ] `curl http://127.0.0.1:8000/health` → `{"status": "healthy"}`
- [ ] `curl http://127.0.0.1:8000/api/v1/cinemas` → lista kin (może być pusta)
- [ ] Otwórz `/docs` w przeglądarce → widoczne endpointy
- [ ] Uruchom Interactive CLI: `python scripts/test_api.py`
- [ ] Zarejestruj użytkownika i utwórz rezerwację

---

## 🎯 Next Steps

1. **Załaduj dane**: `python scripts/load_sample_data.py`
2. **Testuj CLI**: `python scripts/test_api.py`
3. **Czytaj kod**: `/src` → Understanding architecture
4. **Dodaj endpointy**: Postępuj wg AGENTS.md
5. **Deploy**: `docker-compose up` na serwerze

---

Powodzenia! 🎬🍿
