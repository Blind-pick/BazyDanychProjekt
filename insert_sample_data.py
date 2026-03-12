import psycopg


def insert_sample_data():
    conn = psycopg.connect(
        host="localhost",
        dbname="kino",
        user="postgres",
        password="pswd"
    )

    with conn.cursor() as cur:

        # CINEMAS
        cur.execute("INSERT INTO cinemas (name, city) VALUES (%s, %s)", ("Cinema City", "Wrocław"))
        cur.execute("INSERT INTO cinemas (name, city) VALUES (%s, %s)", ("Helios", "Warszawa"))

        # HALL TYPES
        cur.execute("INSERT INTO hall_types (name) VALUES (%s)", ("Standard",))
        cur.execute("INSERT INTO hall_types (name) VALUES (%s)", ("IMAX",))

        # HALLS
        cur.execute("INSERT INTO halls (cinema_id, hall_type_id, name, capacity) VALUES (1, 1, 'Sala 1', 120)")
        cur.execute("INSERT INTO halls (cinema_id, hall_type_id, name, capacity) VALUES (1, 2, 'Sala IMAX', 250)")

        # SEAT TYPES
        cur.execute("INSERT INTO seat_types (name) VALUES (%s)", ("Normal",))
        cur.execute("INSERT INTO seat_types (name) VALUES (%s)", ("VIP",))

        # SEATS
        cur.execute("INSERT INTO seats (hall_id, seat_type_id, row_label, seat_number) VALUES (1, 1, 'A', 1)")
        cur.execute("INSERT INTO seats (hall_id, seat_type_id, row_label, seat_number) VALUES (1, 2, 'A', 2)")

        # MOVIES
        cur.execute("INSERT INTO movies (title, duration_minutes) VALUES (%s, %s)", ("Inception", 148))
        cur.execute("INSERT INTO movies (title, duration_minutes) VALUES (%s, %s)", ("Avatar", 162))

        # GENRES
        cur.execute("INSERT INTO genres (name) VALUES (%s)", ("Sci-Fi",))
        cur.execute("INSERT INTO genres (name) VALUES (%s)", ("Action",))

        # MOVIE GENRES
        cur.execute("INSERT INTO movie_genres (movie_id, genre_id) VALUES (1, 1)")
        cur.execute("INSERT INTO movie_genres (movie_id, genre_id) VALUES (2, 2)")

        # SHOWTIMES
        cur.execute("INSERT INTO showtimes (movie_id, hall_id, start_datetime, base_price) VALUES (1, 1, '2025-01-01 18:00', 25.00)")
        cur.execute("INSERT INTO showtimes (movie_id, hall_id, start_datetime, base_price) VALUES (2, 2, '2025-01-01 20:00', 35.00)")

        # USERS
        cur.execute("INSERT INTO users (email, username) VALUES (%s, %s)", ("test1@example.com", "user1"))
        cur.execute("INSERT INTO users (email, username) VALUES (%s, %s)", ("test2@example.com", "user2"))

        # RESERVATIONS
        cur.execute("INSERT INTO reservations (user_id, showtime_id, status) VALUES (1, 1, 'pending')")
        cur.execute("INSERT INTO reservations (user_id, showtime_id, status) VALUES (2, 2, 'confirmed')")

        # RESERVATION SEATS
        cur.execute("INSERT INTO reservation_seats (reservation_id, seat_id) VALUES (1, 1)")
        cur.execute("INSERT INTO reservation_seats (reservation_id, seat_id) VALUES (2, 2)")

        # TICKET GROUPS
        cur.execute("INSERT INTO ticket_groups (group_name) VALUES (%s)", ("Normalny",))
        cur.execute("INSERT INTO ticket_groups (group_name) VALUES (%s)", ("Ulgowy",))

        # PROMOTIONS
        cur.execute("INSERT INTO promotions (name, discount_value) VALUES (%s, %s)", ("Promo 10%", 10.00))
        cur.execute("INSERT INTO promotions (name, discount_value) VALUES (%s, %s)", ("Promo 20%", 20.00))

        # PROMOTION RULES
        cur.execute("INSERT INTO promotion_rules (promotion_id) VALUES (1)")
        cur.execute("INSERT INTO promotion_rules (promotion_id) VALUES (2)")

        # TICKETS
        cur.execute("""
            INSERT INTO tickets (showtime_id, seat_id, user_id, reservation_id, ticket_group_id, promotion_id, final_price, status)
            VALUES (1, 1, 1, 1, 1, 1, 20.00, 'valid')
        """)
        cur.execute("""
            INSERT INTO tickets (showtime_id, seat_id, user_id, reservation_id, ticket_group_id, promotion_id, final_price, status)
            VALUES (2, 2, 2, 2, 2, 2, 15.00, 'valid')
        """)

        # PAYMENT METHODS
        cur.execute("INSERT INTO payment_methods (name) VALUES (%s)", ("Karta",))
        cur.execute("INSERT INTO payment_methods (name) VALUES (%s)", ("BLIK",))

        # PAYMENTS
        cur.execute("INSERT INTO payments (user_id, payment_method_id, amount, status) VALUES (1, 1, 20.00, 'completed')")
        cur.execute("INSERT INTO payments (user_id, payment_method_id, amount, status) VALUES (2, 2, 15.00, 'completed')")

        # TICKET PAYMENTS
        cur.execute("INSERT INTO ticket_payments (ticket_id, payment_id, amount) VALUES (1, 1, 20.00)")
        cur.execute("INSERT INTO ticket_payments (ticket_id, payment_id, amount) VALUES (2, 2, 15.00)")

        # CANCELLATION POLICIES
        cur.execute("INSERT INTO cancellation_policies (name, refund_percent) VALUES (%s, %s)", ("Standard", 50.00))
        cur.execute("INSERT INTO cancellation_policies (name, refund_percent) VALUES (%s, %s)", ("Full Refund", 100.00))

        # REFUNDS
        cur.execute("INSERT INTO refunds (ticket_id, payment_id, policy_id, refund_amount) VALUES (1, 1, 1, 10.00)")
        cur.execute("INSERT INTO refunds (ticket_id, payment_id, policy_id, refund_amount) VALUES (2, 2, 2, 15.00)")

    conn.commit()
    conn.close()
    print("Dodano przykładowe dane do bazy.")


if __name__ == "__main__":
    insert_sample_data()
