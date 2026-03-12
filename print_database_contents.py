import psycopg


def print_table(cur, table_name):
    print(f"\n=== {table_name.upper()} ===")
    cur.execute(f"SELECT * FROM {table_name};")
    rows = cur.fetchall()

    if not rows:
        print("(brak danych)")
        return

    for row in rows:
        print(row)


def main():
    conn = psycopg.connect(
        host="localhost",
        dbname="kino",
        user="postgres",
        password="pswd"
    )

    with conn.cursor() as cur:
        tables = [
            "cinemas",
            "hall_types",
            "halls",
            "seat_types",
            "seats",
            "movies",
            "genres",
            "movie_genres",
            "showtimes",
            "users",
            "reservations",
            "reservation_seats",
            "ticket_groups",
            "promotions",
            "promotion_rules",
            "tickets",
            "payment_methods",
            "payments",
            "ticket_payments",
            "cancellation_policies",
            "refunds"
        ]

        for table in tables:
            print_table(cur, table)

    conn.close()


if __name__ == "__main__":
    main()
