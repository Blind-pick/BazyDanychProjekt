#!/bin/sh
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  echo "Waiting for database..."
  sleep 2
done
python main.py
exec uvicorn db_interface:app --host 0.0.0.0 --port 8000
