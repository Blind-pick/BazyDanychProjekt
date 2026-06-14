SET maintenance_work_mem = '1GB';
SET max_parallel_maintenance_workers = 4;

DROP INDEX IF EXISTS idx_tickets_status;

DROP INDEX IF EXISTS idx_tickets_user_id;
CREATE INDEX IF NOT EXISTS idx_tickets_user_created ON tickets (user_id, created_at DESC);

DROP INDEX IF EXISTS idx_reservations_status;
CREATE INDEX IF NOT EXISTS idx_reservations_pending ON reservations (created_at) WHERE status = 'pending';

DROP INDEX IF EXISTS idx_reservations_user_id;
CREATE INDEX IF NOT EXISTS idx_reservations_user_created ON reservations (user_id, created_at DESC);

ANALYZE tickets;
ANALYZE reservations;
ANALYZE cinemas;
