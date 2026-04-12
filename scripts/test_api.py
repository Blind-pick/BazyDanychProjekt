#!/usr/bin/env python3

import requests
import json
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def print_response(response: requests.Response, title: str = "") -> None:
    
    if title:
        print(f"\n{title}")
    print(f"  Status: {response.status_code}")
    try:
        data = response.json()
        print(f"  Response:\n{json.dumps(data, indent=4, ensure_ascii=False, default=str)}")
    except:
        print(f"  Body: {response.text}")

session = {
    "cinema_id": None,
    "hall_id": None,
    "movie_id": None,
    "showtime_id": None,
    "user_id": None,
    "reservation_id": None,
    "ticket_id": None,
    "payment_id": None,
}


def cmd_register_user(base_url: str) -> None:
    
    email = input("  Email: ").strip()
    username = input("  Username: ").strip()
    
    resp = requests.post(
        f"{base_url}/api/v1/users",
        json={"email": email, "username": username}
    )
    print_response(resp, "Register User")
    
    if resp.status_code == 201:
        session["user_id"] = resp.json()["user_id"]
        print(f"  ✓ User registered. ID: {session['user_id']}")


def cmd_create_cinema(base_url: str) -> None:
    
    name = input("  Cinema name: ").strip()
    city = input("  City: ").strip()
    
    resp = requests.post(
        f"{base_url}/api/v1/cinemas",
        json={"name": name, "city": city}
    )
    print_response(resp, "Create Cinema")
    
    if resp.status_code == 201:
        session["cinema_id"] = resp.json()["cinema_id"]
        print(f"  ✓ Cinema created. ID: {session['cinema_id']}")


def cmd_list_cinemas(base_url: str) -> None:
    
    city = input("  Filter by city (empty for all): ").strip() or None
    
    params = {}
    if city:
        params["city"] = city
    
    resp = requests.get(f"{base_url}/api/v1/cinemas", params=params)
    print_response(resp, "List Cinemas")
    
    if resp.status_code == 200:
        data = resp.json()
        for cinema in data.get("items", []):
            session["cinema_id"] = cinema["cinema_id"]
        print(f"  Total: {data.get('total', 0)}")


def cmd_create_reservation(base_url: str) -> None:
    
    if not session["user_id"]:
        print("  ✗ Must register user first")
        return
    if not session["showtime_id"]:
        print("  ✗ Must select showtime first")
        return
    
    print("  Enter seat IDs (comma-separated, e.g., 1,2,3):")
    seat_ids_str = input("  Seat IDs: ").strip()
    seat_ids = [int(x.strip()) for x in seat_ids_str.split(",") if x.strip().isdigit()]
    
    if not seat_ids:
        print("  ✗ No valid seat IDs provided")
        return
    
    resp = requests.post(
        f"{base_url}/api/v1/reservations",
        json={
            "user_id": session["user_id"],
            "showtime_id": session["showtime_id"],
            "seat_ids": seat_ids
        }
    )
    print_response(resp, "Create Reservation")
    
    if resp.status_code == 201:
        session["reservation_id"] = resp.json()["reservation_id"]
        print(f"  ✓ Reservation created. ID: {session['reservation_id']}")


def cmd_get_user_reservations(base_url: str) -> None:
    
    if not session["user_id"]:
        print("  ✗ Must register user first")
        return
    
    resp = requests.get(f"{base_url}/api/v1/users/{session['user_id']}/reservations")
    print_response(resp, "User Reservations")


def cmd_get_user_tickets(base_url: str) -> None:
    
    if not session["user_id"]:
        print("  ✗ Must register user first")
        return
    
    resp = requests.get(f"{base_url}/api/v1/users/{session['user_id']}/tickets")
    print_response(resp, "User Tickets")


def cmd_get_showtime_seats(base_url: str) -> None:
    
    if not session["showtime_id"]:
        print("  ✗ Must select showtime first")
        return
    
    resp = requests.get(f"{base_url}/api/v1/tickets/showtime/{session['showtime_id']}/seats")
    print_response(resp, "Showtime Seats")
    
    if resp.status_code == 200:
        seats = resp.json()
        available_count = sum(1 for s in seats if s["is_available"])
        print(f"  Average price: {seats[0]['base_price'] if seats else 'N/A'}")
        print(f"  Available: {available_count}/{len(seats)}")


def cmd_create_payment(base_url: str) -> None:
    
    if not session["user_id"]:
        print("  ✗ Must register user first")
        return
    
    amount = float(input("  Amount: ") or "29.99")
    method_id = int(input("  Payment method ID (1=Credit, 2=Debit, 3=PayPal, 4=Cash): ") or "1")
    
    resp = requests.post(
        f"{base_url}/api/v1/payments",
        json={
            "user_id": session["user_id"],
            "payment_method_id": method_id,
            "amount": amount,
            "status": "pending",
            "ticket_ids": []
        }
    )
    print_response(resp, "Create Payment")
    
    if resp.status_code == 201:
        session["payment_id"] = resp.json()["payment_id"]
        print(f"  ✓ Payment created. ID: {session['payment_id']}")


def cmd_show_session(base_url: str) -> None:
    
    print("\n  ═══ Session State ═══")
    for key, value in session.items():
        status = "✓" if value else "○"
        print(f"  {status} {key:20s}: {value}")
    print()


def cmd_help(base_url: str = "") -> None:
    
    print("""
  ═══ Cinema API - Available Commands ═══
  
  Users:
    1. register        - Register a new user
    2. user_tickets    - Get user's tickets
    3. user_reservations - Get user's reservations
  
  Cinemas:
    4. create_cinema   - Create a new cinema
    5. list_cinemas    - List all cinemas
  
  Reservations:
    6. create_reservation - Reserve seats for a showtime
    7. get_seats       - Get available seats for showtime
  
  Payments:
    8. create_payment  - Create a payment record
  
  Utilities:
    9. session         - Show session state
    10. health          - Check API health
    11. help            - Show this menu
    0.  exit            - Exit program
    """)


def cmd_health(base_url: str) -> None:
    
    try:
        resp = requests.get(f"{base_url}/health")
        print_response(resp, "API Health Check")
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Cannot connect to API at {base_url}")


commands = {
    "1": ("Register User", cmd_register_user),
    "2": ("Get User Tickets", cmd_get_user_tickets),
    "3": ("Get User Reservations", cmd_get_user_reservations),
    "4": ("Create Cinema", cmd_create_cinema),
    "5": ("List Cinemas", cmd_list_cinemas),
    "6": ("Create Reservation", cmd_create_reservation),
    "7": ("Get Showtime Seats", cmd_get_showtime_seats),
    "8": ("Create Payment", cmd_create_payment),
    "9": ("Session State", cmd_show_session),
    "10": ("API Health", cmd_health),
    "11": ("Help", cmd_help),
}


def main():
    parser = argparse.ArgumentParser(description="Cinema Reservation API Client")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help=f"API base URL (default: {DEFAULT_BASE_URL})")
    args = parser.parse_args()
    
    print(f"\n  Cinema Reservation API Client")
    print(f"  API: {args.url}")
    print(f"  Type 'help' or '11' for available commands\n")
    
    while True:
        try:
            choice = input("  > ").strip()
            
            if choice == "0" or choice.lower() == "exit":
                print("  Goodbye!")
                break
            
            if choice.lower() == "help":
                cmd_help(args.url)
            elif choice in commands:
                name, cmd = commands[choice]
                try:
                    cmd(args.url)
                except Exception as e:
                    print(f"  ✗ Error: {e}")
            else:
                print("  ✗ Unknown command. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\n  Interrupted")
            break
        except Exception as e:
            print(f"  ✗ Error: {e}")


if __name__ == "__main__":
    main()
