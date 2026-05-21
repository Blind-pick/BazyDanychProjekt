\set u_id random(1, 5000)
\set s_id random(1, 100000)

BEGIN;

INSERT INTO reservations (user_id, showtime_id, status)
SELECT u.user_id, s.showtime_id, 'confirmed'
FROM users u, showtimes s
WHERE u.user_id = :u_id AND s.showtime_id = :s_id
LIMIT 1;

COMMIT;