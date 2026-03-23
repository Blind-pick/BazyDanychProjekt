import requests
import json
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone

DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Cinema Reservation API - interactive endpoint tester")
    parser.add_argument("--url", type=str, default=DEFAULT_BASE_URL, help="Base URL of the API (default: $API_BASE_URL or http://127.0.0.1:8000)")
    return parser.parse_args()


def print_response(response: requests.Response):
    print(f"\n  Status: {response.status_code}")
    try:
        parsed = response.json()
        print(f"  Body:\n{json.dumps(parsed, indent=4, ensure_ascii=False, default=str)}")
    except Exception:
        print(f"  Body (raw): {response.text}")


def prompt_int(label: str, default: int = None) -> int:
    default_hint = f" [{default}]" if default is not None else ""
    raw = input(f"  {label}{default_hint}: ").strip()
    if raw == "" and default is not None:
        return default
    return int(raw)


def prompt_str(label: str, default: str = None) -> str:
    default_hint = f" [{default}]" if default is not None else ""
    raw = input(f"  {label}{default_hint}: ").strip()
    if raw == "" and default is not None:
        return default
    return raw


def prompt_optional_str(label: str) -> str | None:
    raw = input(f"  {label} (Enter to skip): ").strip()
    return raw if raw else None


def prompt_optional_int(label: str) -> int | None:
    raw = input(f"  {label} (Enter to skip): ").strip()
    return int(raw) if raw else None


session_state = {
    "user_id": None,
    "cinema_id": None,
    "hall_id": None,
    "seat_id": None,
    "movie_id": None,
    "genre_id": None,
    "showtime_id": None,
    "reservation_id": None,
    "ticket_id": None,
    "payment_id": None,
}


def print_session_state():
    print("\n  --- Session state (IDs from this run) ---")
    for key, value in session_state.items():
        print(f"  {key}: {value}")
    print()


def action_setup_all(base_url: str):
    print("\n  [SETUP] Creating all prerequisite test data...\n")

    timestamp = datetime.now().strftime("%H%M%S")

    response = requests.post(f"{base_url}/api/v1/users", json={
        "email": f"testuser_{timestamp}@example.com",
        "username": f"testuser_{timestamp}"
    })
    print("  POST /api/v1/users")
    print_response(response)
    if response.status_code == 201:
        session_state["user_id"] = response.json()["user_id"]

    response = requests.post(f"{base_url}/api/v1/cinemas", json={
        "name": f"Test Cinema {timestamp}",
        "city": "Warszawa"
    })
    print("\n  POST /api/v1/cinemas")
    print_response(response)
    if response.status_code == 201:
        session_state["cinema_id"] = response.json()["cinema_id"]

    if session_state["cinema_id"]:
        response = requests.post(f"{base_url}/api/v1/halls", json={
            "cinema_id": session_state["cinema_id"],
            "hall_type_id": 1,
            "name": f"Sala Test {timestamp}",
            "capacity": 50
        })
        print("\n  POST /api/v1/halls")
        print_response(response)
        if response.status_code == 201:
            session_state["hall_id"] = response.json()["hall_id"]

    if session_state["hall_id"]:
        response = requests.post(f"{base_url}/api/v1/seats", json={
            "hall_id": session_state["hall_id"],
            "seat_type_id": 1,
            "row_label": "A",
            "seat_number": 1
        })
        print("\n  POST /api/v1/seats")
        print_response(response)
        if response.status_code == 201:
            session_state["seat_id"] = response.json()["seat_id"]

    response = requests.post(f"{base_url}/api/v1/movies", json={
        "title": f"Test Movie {timestamp}",
        "duration_minutes": 120
    })
    print("\n  POST /api/v1/movies")
    print_response(response)
    if response.status_code == 201:
        session_state["movie_id"] = response.json()["movie_id"]

    response = requests.post(f"{base_url}/api/v1/genres", json={
        "name": f"TestGenre{timestamp}"
    })
    print("\n  POST /api/v1/genres")
    print_response(response)
    if response.status_code == 201:
        session_state["genre_id"] = response.json()["genre_id"]

    if session_state["movie_id"] and session_state["hall_id"]:
        future_datetime = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
        response = requests.post(f"{base_url}/api/v1/showtimes", json={
            "movie_id": session_state["movie_id"],
            "hall_id": session_state["hall_id"],
            "start_datetime": future_datetime,
            "base_price": 30.00
        })
        print("\n  POST /api/v1/showtimes")
        print_response(response)
        if response.status_code == 201:
            session_state["showtime_id"] = response.json()["showtime_id"]

    if session_state["user_id"] and session_state["showtime_id"] and session_state["seat_id"]:
        response = requests.post(f"{base_url}/api/v1/reservations", json={
            "user_id": session_state["user_id"],
            "showtime_id": session_state["showtime_id"],
            "seat_ids": [session_state["seat_id"]]
        })
        print("\n  POST /api/v1/reservations")
        print_response(response)
        if response.status_code == 201:
            session_state["reservation_id"] = response.json()["reservation_id"]

    print("\n  [SETUP] Done.")
    print_session_state()


def action_list_cinemas(base_url: str):
    city = prompt_optional_str("Filter by city")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if city:
        params["city"] = city
    response = requests.get(f"{base_url}/api/v1/cinemas", params=params)
    print_response(response)


def action_create_cinema(base_url: str):
    name = prompt_str("Cinema name")
    city = prompt_str("City")
    response = requests.post(f"{base_url}/api/v1/cinemas", json={"name": name, "city": city})
    print_response(response)
    if response.status_code == 201:
        session_state["cinema_id"] = response.json()["cinema_id"]


def action_list_halls(base_url: str):
    cinema_id = prompt_optional_int("Filter by cinema_id")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if cinema_id:
        params["cinema_id"] = cinema_id
    response = requests.get(f"{base_url}/api/v1/halls", params=params)
    print_response(response)


def action_create_hall(base_url: str):
    cinema_id = prompt_int("cinema_id", session_state["cinema_id"])
    hall_type_id = prompt_int("hall_type_id", 1)
    name = prompt_str("Hall name", "Sala 1")
    capacity = prompt_int("capacity", 100)
    response = requests.post(f"{base_url}/api/v1/halls", json={
        "cinema_id": cinema_id, "hall_type_id": hall_type_id,
        "name": name, "capacity": capacity
    })
    print_response(response)
    if response.status_code == 201:
        session_state["hall_id"] = response.json()["hall_id"]


def action_list_seats(base_url: str):
    hall_id = prompt_optional_int("Filter by hall_id")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if hall_id:
        params["hall_id"] = hall_id
    response = requests.get(f"{base_url}/api/v1/seats", params=params)
    print_response(response)


def action_create_seat(base_url: str):
    hall_id = prompt_int("hall_id", session_state["hall_id"])
    seat_type_id = prompt_int("seat_type_id", 1)
    row_label = prompt_str("row_label", "A")
    seat_number = prompt_int("seat_number", 1)
    response = requests.post(f"{base_url}/api/v1/seats", json={
        "hall_id": hall_id, "seat_type_id": seat_type_id,
        "row_label": row_label, "seat_number": seat_number
    })
    print_response(response)
    if response.status_code == 201:
        session_state["seat_id"] = response.json()["seat_id"]


def action_list_movies(base_url: str):
    title = prompt_optional_str("Filter by title (partial)")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if title:
        params["title"] = title
    response = requests.get(f"{base_url}/api/v1/movies", params=params)
    print_response(response)


def action_create_movie(base_url: str):
    title = prompt_str("Title", "Test Movie")
    duration_minutes = prompt_int("duration_minutes", 120)
    response = requests.post(f"{base_url}/api/v1/movies", json={
        "title": title, "duration_minutes": duration_minutes
    })
    print_response(response)
    if response.status_code == 201:
        session_state["movie_id"] = response.json()["movie_id"]


def action_list_genres(base_url: str):
    name = prompt_optional_str("Filter by name (partial)")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if name:
        params["name"] = name
    response = requests.get(f"{base_url}/api/v1/genres", params=params)
    print_response(response)


def action_create_genre(base_url: str):
    name = prompt_str("Genre name", "Drama")
    response = requests.post(f"{base_url}/api/v1/genres", json={"name": name})
    print_response(response)
    if response.status_code == 201:
        session_state["genre_id"] = response.json()["genre_id"]


def action_list_showtimes(base_url: str):
    from_datetime = prompt_optional_str("from_datetime (e.g. 2025-01-01T00:00:00)")
    to_datetime = prompt_optional_str("to_datetime (e.g. 2026-12-31T23:59:59)")
    movie_id = prompt_optional_int("Filter by movie_id")
    hall_id = prompt_optional_int("Filter by hall_id")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if from_datetime:
        params["from_datetime"] = from_datetime
    if to_datetime:
        params["to_datetime"] = to_datetime
    if movie_id:
        params["movie_id"] = movie_id
    if hall_id:
        params["hall_id"] = hall_id
    response = requests.get(f"{base_url}/api/v1/showtimes", params=params)
    print_response(response)


def action_create_showtime(base_url: str):
    movie_id = prompt_int("movie_id", session_state["movie_id"])
    hall_id = prompt_int("hall_id", session_state["hall_id"])
    default_start = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
    start_datetime = prompt_str("start_datetime", default_start)
    base_price = float(prompt_str("base_price", "25.00"))
    response = requests.post(f"{base_url}/api/v1/showtimes", json={
        "movie_id": movie_id, "hall_id": hall_id,
        "start_datetime": start_datetime, "base_price": base_price
    })
    print_response(response)
    if response.status_code == 201:
        session_state["showtime_id"] = response.json()["showtime_id"]


def action_get_showtime_seats(base_url: str):
    showtime_id = prompt_int("showtime_id", session_state["showtime_id"])
    response = requests.get(f"{base_url}/api/v1/showtimes/{showtime_id}/seats")
    print_response(response)


def action_register_user(base_url: str):
    email = prompt_str("email", "newuser@example.com")
    username = prompt_str("username", "newuser")
    response = requests.post(f"{base_url}/api/v1/users", json={"email": email, "username": username})
    print_response(response)
    if response.status_code == 201:
        session_state["user_id"] = response.json()["user_id"]


def action_get_user_tickets(base_url: str):
    user_id = prompt_int("user_id", session_state["user_id"])
    from_datetime = prompt_optional_str("from_datetime (e.g. 2025-01-01T00:00:00)")
    to_datetime = prompt_optional_str("to_datetime (e.g. 2026-12-31T23:59:59)")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if from_datetime:
        params["from_datetime"] = from_datetime
    if to_datetime:
        params["to_datetime"] = to_datetime
    response = requests.get(f"{base_url}/api/v1/users/{user_id}/tickets", params=params)
    print_response(response)


def action_get_user_reservations(base_url: str):
    user_id = prompt_int("user_id", session_state["user_id"])
    reservation_status = prompt_optional_str("Filter by status (pending/confirmed/cancelled)")
    from_datetime = prompt_optional_str("from_datetime (e.g. 2025-01-01T00:00:00)")
    to_datetime = prompt_optional_str("to_datetime (e.g. 2026-12-31T23:59:59)")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if reservation_status:
        params["reservation_status"] = reservation_status
    if from_datetime:
        params["from_datetime"] = from_datetime
    if to_datetime:
        params["to_datetime"] = to_datetime
    response = requests.get(f"{base_url}/api/v1/users/{user_id}/reservations", params=params)
    print_response(response)


def action_get_user_payments(base_url: str):
    user_id = prompt_int("user_id", session_state["user_id"])
    from_datetime = prompt_optional_str("from_datetime (e.g. 2025-01-01T00:00:00)")
    to_datetime = prompt_optional_str("to_datetime (e.g. 2026-12-31T23:59:59)")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if from_datetime:
        params["from_datetime"] = from_datetime
    if to_datetime:
        params["to_datetime"] = to_datetime
    response = requests.get(f"{base_url}/api/v1/users/{user_id}/payments", params=params)
    print_response(response)


def action_get_user_refunds(base_url: str):
    user_id = prompt_int("user_id", session_state["user_id"])
    from_datetime = prompt_optional_str("from_datetime (e.g. 2025-01-01T00:00:00)")
    to_datetime = prompt_optional_str("to_datetime (e.g. 2026-12-31T23:59:59)")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if from_datetime:
        params["from_datetime"] = from_datetime
    if to_datetime:
        params["to_datetime"] = to_datetime
    response = requests.get(f"{base_url}/api/v1/users/{user_id}/refunds", params=params)
    print_response(response)


def action_list_reservations(base_url: str):
    user_id = prompt_optional_int("Filter by user_id")
    from_datetime = prompt_optional_str("from_datetime (e.g. 2025-01-01T00:00:00)")
    to_datetime = prompt_optional_str("to_datetime (e.g. 2026-12-31T23:59:59)")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if user_id:
        params["user_id"] = user_id
    if from_datetime:
        params["from_datetime"] = from_datetime
    if to_datetime:
        params["to_datetime"] = to_datetime
    response = requests.get(f"{base_url}/api/v1/reservations", params=params)
    print_response(response)


def action_create_reservation(base_url: str):
    user_id = prompt_int("user_id", session_state["user_id"])
    showtime_id = prompt_int("showtime_id", session_state["showtime_id"])
    seat_id = prompt_int("seat_id (single)", session_state["seat_id"])
    response = requests.post(f"{base_url}/api/v1/reservations", json={
        "user_id": user_id,
        "showtime_id": showtime_id,
        "seat_ids": [seat_id]
    })
    print_response(response)
    if response.status_code == 201:
        session_state["reservation_id"] = response.json()["reservation_id"]


def action_update_reservation_status(base_url: str):
    reservation_id = prompt_int("reservation_id", session_state["reservation_id"])
    new_status = prompt_str("New status (pending/confirmed/cancelled)", "confirmed")
    response = requests.put(
        f"{base_url}/api/v1/reservations/{reservation_id}/status",
        json={"status": new_status}
    )
    print_response(response)


def action_delete_reservation(base_url: str):
    reservation_id = prompt_int("reservation_id", session_state["reservation_id"])
    response = requests.delete(f"{base_url}/api/v1/reservations/{reservation_id}")
    print(f"\n  Status: {response.status_code}")
    if response.status_code == 204:
        print("  Reservation deleted successfully.")
        if session_state["reservation_id"] == reservation_id:
            session_state["reservation_id"] = None


def action_purchase_ticket(base_url: str):
    reservation_id = prompt_int("reservation_id", session_state["reservation_id"])
    user_id = prompt_int("user_id", session_state["user_id"])
    payment_method_id = prompt_int("payment_method_id (1=Karta, 2=BLIK)", 1)
    ticket_group_id = prompt_int("ticket_group_id (1=Normalny, 2=Ulgowy)", 1)
    promotion_id = prompt_optional_int("promotion_id")
    response = requests.post(f"{base_url}/api/v1/tickets/purchase", json={
        "reservation_id": reservation_id,
        "user_id": user_id,
        "payment_method_id": payment_method_id,
        "ticket_group_id": ticket_group_id,
        "promotion_id": promotion_id
    })
    print_response(response)
    if response.status_code == 200:
        session_state["ticket_id"] = response.json()["ticket_id"]


def action_list_tickets(base_url: str):
    user_id = prompt_optional_int("Filter by user_id")
    reservation_id = prompt_optional_int("Filter by reservation_id")
    from_datetime = prompt_optional_str("from_datetime (e.g. 2025-01-01T00:00:00)")
    to_datetime = prompt_optional_str("to_datetime (e.g. 2026-12-31T23:59:59)")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if user_id:
        params["user_id"] = user_id
    if reservation_id:
        params["reservation_id"] = reservation_id
    if from_datetime:
        params["from_datetime"] = from_datetime
    if to_datetime:
        params["to_datetime"] = to_datetime
    response = requests.get(f"{base_url}/api/v1/tickets", params=params)
    print_response(response)


def action_list_payments(base_url: str):
    user_id = prompt_optional_int("Filter by user_id")
    from_datetime = prompt_optional_str("from_datetime (e.g. 2025-01-01T00:00:00)")
    to_datetime = prompt_optional_str("to_datetime (e.g. 2026-12-31T23:59:59)")
    skip = prompt_int("skip", 0)
    limit = prompt_int("limit", 20)
    params = {"skip": skip, "limit": limit}
    if user_id:
        params["user_id"] = user_id
    if from_datetime:
        params["from_datetime"] = from_datetime
    if to_datetime:
        params["to_datetime"] = to_datetime
    response = requests.get(f"{base_url}/api/v1/payments", params=params)
    print_response(response)


def action_sales_report(base_url: str):
    from_datetime = prompt_optional_str("from_datetime (e.g. 2025-01-01T00:00:00)")
    to_datetime = prompt_optional_str("to_datetime (e.g. 2026-12-31T23:59:59)")
    params = {}
    if from_datetime:
        params["from_datetime"] = from_datetime
    if to_datetime:
        params["to_datetime"] = to_datetime
    response = requests.get(f"{base_url}/api/v1/reports/sales", params=params)
    print_response(response)


# ──────────────────────────────────────────────
# MENU DEFINITION
# ──────────────────────────────────────────────

MENU_SECTIONS = [
    {
        "title": "SETUP",
        "entries": [
            ("Create all test data at once (user, cinema, hall, seat, movie, showtime, reservation)", action_setup_all),
            ("Show current session state (created IDs)", lambda base_url: print_session_state()),
        ]
    },
    {
        "title": "USERS",
        "entries": [
            ("POST   /api/v1/users                          Register new user", action_register_user),
            ("GET    /api/v1/users/{id}/tickets             User ticket history", action_get_user_tickets),
            ("GET    /api/v1/users/{id}/reservations        User reservation history", action_get_user_reservations),
            ("GET    /api/v1/users/{id}/payments            User payment history", action_get_user_payments),
            ("GET    /api/v1/users/{id}/refunds             User refund history", action_get_user_refunds),
        ]
    },
    {
        "title": "CINEMAS",
        "entries": [
            ("GET    /api/v1/cinemas                        List cinemas", action_list_cinemas),
            ("POST   /api/v1/cinemas                        Create cinema", action_create_cinema),
        ]
    },
    {
        "title": "HALLS",
        "entries": [
            ("GET    /api/v1/halls                          List halls", action_list_halls),
            ("POST   /api/v1/halls                          Create hall", action_create_hall),
        ]
    },
    {
        "title": "SEATS",
        "entries": [
            ("GET    /api/v1/seats                          List seats", action_list_seats),
            ("POST   /api/v1/seats                          Create seat", action_create_seat),
        ]
    },
    {
        "title": "MOVIES",
        "entries": [
            ("GET    /api/v1/movies                         List movies", action_list_movies),
            ("POST   /api/v1/movies                         Create movie", action_create_movie),
        ]
    },
    {
        "title": "GENRES",
        "entries": [
            ("GET    /api/v1/genres                         List genres", action_list_genres),
            ("POST   /api/v1/genres                         Create genre", action_create_genre),
        ]
    },
    {
        "title": "SHOWTIMES",
        "entries": [
            ("GET    /api/v1/showtimes                      List showtimes", action_list_showtimes),
            ("POST   /api/v1/showtimes                      Create showtime", action_create_showtime),
            ("GET    /api/v1/showtimes/{id}/seats           Seat availability for showtime", action_get_showtime_seats),
        ]
    },
    {
        "title": "RESERVATIONS",
        "entries": [
            ("GET    /api/v1/reservations                   List reservations", action_list_reservations),
            ("POST   /api/v1/reservations                   Create reservation", action_create_reservation),
            ("PUT    /api/v1/reservations/{id}/status       Update reservation status", action_update_reservation_status),
            ("DELETE /api/v1/reservations/{id}              Delete reservation", action_delete_reservation),
        ]
    },
    {
        "title": "TICKETS",
        "entries": [
            ("POST   /api/v1/tickets/purchase               Purchase ticket", action_purchase_ticket),
            ("GET    /api/v1/tickets                        List tickets", action_list_tickets),
        ]
    },
    {
        "title": "PAYMENTS",
        "entries": [
            ("GET    /api/v1/payments                       List payments", action_list_payments),
        ]
    },
    {
        "title": "REPORTS",
        "entries": [
            ("GET    /api/v1/reports/sales                  Sales report", action_sales_report),
        ]
    },
]


def build_flat_menu():
    flat_entries = []
    display_lines = []
    index = 1
    for section in MENU_SECTIONS:
        display_lines.append(f"\n  ── {section['title']} ──")
        for label, action in section["entries"]:
            display_lines.append(f"  [{index:>2}] {label}")
            flat_entries.append((label, action))
            index += 1
    display_lines.append("\n  [ 0] Exit")
    return flat_entries, display_lines


def main():
    args = parse_arguments()
    base_url = args.url.rstrip("/")

    flat_entries, display_lines = build_flat_menu()

    print(f"\n  Cinema Reservation API — Interactive Tester")
    print(f"  Target: {base_url}\n")

    while True:
        print("\n" + "=" * 60)
        for line in display_lines:
            print(line)
        print()

        raw_choice = input("  Select option: ").strip()

        if raw_choice == "0":
            print("\n  Exiting.\n")
            sys.exit(0)

        if not raw_choice.isdigit():
            print("\n  Invalid input. Enter a number.")
            continue

        choice_index = int(raw_choice) - 1

        if choice_index < 0 or choice_index >= len(flat_entries):
            print(f"\n  Option out of range. Choose 1–{len(flat_entries)} or 0 to exit.")
            continue

        label, action = flat_entries[choice_index]
        print(f"\n  >>> {label}\n")

        try:
            action(base_url)
        except requests.exceptions.ConnectionError:
            print(f"\n  ERROR: Could not connect to {base_url}. Is the API running?")
        except KeyboardInterrupt:
            print("\n  Cancelled.")
        except Exception as exception:
            print(f"\n  ERROR: {exception}")

        input("\n  Press Enter to return to menu...")


if __name__ == "__main__":
    main()