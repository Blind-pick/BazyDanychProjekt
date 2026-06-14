#!/usr/bin/env bash

set -euo pipefail
cd "$(dirname "$0")/.."


DB_CPUS="${DB_CPUS:-0.4}"
DB_MEMORY="${DB_MEMORY:-256m}"
DB_POOL_TIMEOUT="${DB_POOL_TIMEOUT:-8}"   
API_WORKERS="${API_WORKERS:-4}"
RATE="${RATE:-5}"             
RAMPUP="${RAMPUP:-300}"       
STEPS="${STEPS:-20}"          
HOLD="${HOLD:-60}"            
CONC_LIMIT="${CONC_LIMIT:-1500}"   

export HEAP="${HEAP:--Xms1g -Xmx6g}"

JMETER="${JMETER:-}"
if [ -z "$JMETER" ]; then
  if [ -x "../apache-jmeter-5.6.3/bin/jmeter" ]; then JMETER="../apache-jmeter-5.6.3/bin/jmeter"
  elif command -v jmeter >/dev/null 2>&1; then JMETER="jmeter"
  else echo "BLAD: nie znaleziono jmeter." >&2; exit 1; fi
fi

echo "============================================================"
echo " OPEN-LOOP breakpoint (utrata kontroli)"
echo "   DB limit:    ${DB_CPUS} CPU / ${DB_MEMORY}  (pool_timeout=${DB_POOL_TIMEOUT}s)"
echo "   Rate:        0 -> ${RATE} req/s przez ${RAMPUP}s (${STEPS} schodkow), hold ${HOLD}s"
echo "   Bezpiecznik: ConcurrencyLimit=${CONC_LIMIT} watkow (HEAP=${HEAP})"
echo "============================================================"

echo "==> 1/6 Zaciskam DB do ${DB_CPUS} CPU / ${DB_MEMORY}..."
DB_CPUS="$DB_CPUS" DB_MEMORY="$DB_MEMORY" docker compose up -d db
until docker inspect cinema_db --format '{{.State.Health.Status}}' 2>/dev/null | grep -q healthy; do sleep 2; done
TICKETS=$(docker exec cinema_db psql -U postgres -d kino -tAc "SELECT count(*) FROM tickets" 2>/dev/null | tr -dc '0-9' || echo 0)
if [ "${TICKETS:-0}" -lt 1000000 ]; then
  echo "BLAD: tabela 'tickets' ma ${TICKETS:-0} wierszy (<1 mln). Zaladuj dane:" >&2
  echo "  docker compose up -d db && python3 scripts/load_sample_data.py" >&2
  exit 1
fi
echo "    OK: tickets=${TICKETS} wierszy."

echo "==> 2/6 Monitoring + reload prometheus..."
docker compose up -d prometheus grafana postgres_exporter cadvisor >/dev/null
docker compose restart prometheus >/dev/null 2>&1 || true

echo "==> 3/6 Restart API (${API_WORKERS} workerow)..."
API_WORKERS="$API_WORKERS" DB_CPUS="$DB_CPUS" DB_MEMORY="$DB_MEMORY" DB_POOL_TIMEOUT="$DB_POOL_TIMEOUT" \
  docker compose up -d --build --force-recreate api >/dev/null
until curl -sf localhost:8000/health >/dev/null 2>&1; do sleep 2; done

echo "==> 4/6 Reset pg_stat_statements..."
docker exec cinema_db psql -U postgres -d kino -c "SELECT pg_stat_statements_reset();" >/dev/null

echo "==> 5/6 Regeneruje CSV-ki..."
python3 scripts/generate_perf_csvs.py >/dev/null

OUT="/tmp/jmeter_openloop_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"
echo "==> 6/6 Start JMeter (open-loop) -> raport: ${OUT}/report/index.html"
echo "    PODGLAD: Grafana http://localhost:3000 (dashboard 'Punkt zalamania')"
"$JMETER" -n -t tests/perf_test_openloop.jmx \
  -Jprometheus.ip=0.0.0.0 -Jprometheus.port=9270 \
  -l "${OUT}/results.jtl" -e -o "${OUT}/report" \
  -Jrate="$RATE" -Jrampup="$RAMPUP" -Jsteps="$STEPS" -Jhold="$HOLD" -Jconc_limit="$CONC_LIMIT"

echo "============================================================"
echo " GOTOWE. Raport: ${OUT}/report/index.html"
echo "============================================================"
