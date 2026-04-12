#!/bin/sh
set -e

# Wait for database to be ready
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  echo "Waiting for database to be ready..."
  sleep 2
done

echo "Database is ready. Starting API..."

# Run the FastAPI application with uvicorn
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --log-level info
