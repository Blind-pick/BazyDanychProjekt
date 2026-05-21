BEGIN;

-- Symulacja rzucenia się tysięcy klientów na jeden, "gorący" seans (np. premiera Spider-Mana).
-- Przypisanie tej samej wartości nie psuje danych, ale wymusza założenie blokady (RowExclusiveLock) 
-- na wierszu o ID = 1, zmuszając inne wątki do czekania w kolejce.
UPDATE showtimes 
SET start_datetime = start_datetime 
WHERE showtime_id = 1; 

COMMIT;