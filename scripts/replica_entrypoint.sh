#!/bin/sh

set -e
PGDATA="${PGDATA:-/var/lib/postgresql/data}"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "[replica] pusty wolumen -> pg_basebackup z mastera (db:5432) jako 'replicator'..."
  rm -rf "${PGDATA:?}/"* 2>/dev/null || true
  until pg_basebackup -h db -p 5432 -U replicator -D "$PGDATA" -Fp -Xs -R -P -v; do
    echo "[replica] master jeszcze nie gotowy do replikacji, ponawiam za 3s..."
    sleep 3
  done
  chown -R postgres:postgres "$PGDATA"
  chmod 0700 "$PGDATA"
  echo "[replica] basebackup OK -> start jako STANDBY (read-only)."
else
  echo "[replica] wolumen juz zainicjowany -> start standby."
fi

exec docker-entrypoint.sh "$@"
