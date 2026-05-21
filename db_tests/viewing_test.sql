BEGIN;
SELECT 
    c.city, 
    m.title, 
    COUNT(t.ticket_id) as sprzedane_bilety, 
    SUM(t.final_price) as total_revenue
FROM cinemas c
JOIN halls h ON c.cinema_id = h.cinema_id
JOIN showtimes s ON h.hall_id = s.hall_id
JOIN movies m ON s.movie_id = m.movie_id
LEFT JOIN tickets t ON s.showtime_id = t.showtime_id
WHERE s.start_datetime > NOW() - INTERVAL '3 months'
GROUP BY c.city, m.title
ORDER BY total_revenue DESC
LIMIT 10;
COMMIT;