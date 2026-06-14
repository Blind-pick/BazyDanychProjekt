#!/usr/bin/env bash

set -euo pipefail
cd "$(dirname "$0")/.."

DB_CPUS="${DB_CPUS:-0.3}"           
DB_MEMORY="${DB_MEMORY:-256m}"      
DB_POOL_TIMEOUT="${DB_POOL_TIMEOUT:-5}"  
API_WORKERS="${API_WORKERS:-4}"     
THREADS="${THREADS:-120}"           
RAMPUP="${RAMPUP:-300}"             
HOLD="${HOLD:-150}"                 
SHUTDOWN="${SHUTDOWN:-20}"          


THINK_OFFSET="${THINK_OFFSET:-300}"   
THINK_RANGE="${THINK_RANGE:-1400}"    

export HEAP="${HEAP:--Xms1g -Xmx4g}"

JMETER="${JMETER:-}"
if [ -z "$JMETER" ]; then
  if [ -x "../apache-jmeter-5.6.3/bin/jmeter" ]; then
    JMETER="../apache-jmeter-5.6.3/bin/jmeter"
  elif command -v jmeter >/dev/null 2>&1; then
    JMETER="jmeter"
  else
    echo "BLAD: nie znaleziono jmeter. Ustaw JMETER=/sciezka/do/bin/jmeter" >&2
    exit 1
  fi
fi

echo "============================================================"
echo " PROGRESSIVE OVERLOAD - szukanie punktu zalamania bazy"
echo "   DB limit:    ${DB_CPUS} CPU / ${DB_MEMORY} na WEZEL (master + replika, jesli jest)"
echo "   API:         ${API_WORKERS} workerow, pool_timeout=${DB_POOL_TIMEOUT}s; ODCZYTY->replika, ZAPISY->master"
echo "   Rozped:      0 -> ${THREADS} watkow LINIOWO przez ${RAMPUP}s"
echo "   Hold:        ${HOLD}s na szczycie, potem ${SHUTDOWN}s wygaszania"
echo "   Calosc:      ~$(( (RAMPUP + HOLD + SHUTDOWN) / 60 )) min"
echo "   JMeter:      ${JMETER}  (HEAP=${HEAP})"
echo "============================================================"

echo "==> 1/6 Zaciskam DB (master + replika) do ${DB_CPUS} CPU / ${DB_MEMORY} (dane zostaja)..."

DB_CPUS="$DB_CPUS" DB_MEMORY="$DB_MEMORY" docker compose up -d db db_replica 2>/dev/null || \
  DB_CPUS="$DB_CPUS" DB_MEMORY="$DB_MEMORY" docker compose up -d db
until docker inspect cinema_db --format '{{.State.Health.Status}}' 2>/dev/null | grep -q healthy; do sleep 2; done
if docker inspect cinema_db_replica >/dev/null 2>&1; then
  echo "    czekam na replike (standby)..."
  until docker inspect cinema_db_replica --format '{{.State.Health.Status}}' 2>/dev/null | grep -q healthy; do sleep 2; done
fi


echo "    sprawdzam, czy baza jest zapelniona..."
TICKETS=$(docker exec cinema_db psql -U postgres -d kino -tAc "SELECT count(*) FROM tickets" 2>/dev/null | tr -dc '0-9' || echo 0)
TICKETS=${TICKETS:-0}
if [ "$TICKETS" -lt 1000000 ]; then
  echo "BLAD: tabela 'tickets' ma tylko ${TICKETS} wierszy (<1 mln)." >&2
  echo "      Zaladuj dane PRZY PELNYCH ZASOBACH bazy, np.:" >&2
  echo "        docker compose up -d db && python3 scripts/load_sample_data.py" >&2
  echo "      a potem uruchom ten skrypt ponownie." >&2
  exit 1
fi
echo "    OK: tickets=${TICKETS} wierszy."

echo "==> 2/6 Upewniam sie, ze monitoring dziala (prometheus/grafana/exporter/cadvisor)..."
docker compose up -d prometheus grafana postgres_exporter cadvisor >/dev/null
docker compose restart prometheus >/dev/null 2>&1 || true

echo "==> 3/6 Swiezy restart API z ${API_WORKERS} workerami (przebudowa obrazu + nowa pula)..."

API_WORKERS="$API_WORKERS" DB_CPUS="$DB_CPUS" DB_MEMORY="$DB_MEMORY" DB_POOL_TIMEOUT="$DB_POOL_TIMEOUT" \
  docker compose up -d --build --force-recreate api >/dev/null
echo "    czekam na /health API..."
until curl -sf localhost:8000/health >/dev/null 2>&1; do sleep 2; done

echo "==> 4/6 Reset pg_stat_statements (master + replika)..."
docker exec cinema_db psql -U postgres -d kino -c "SELECT pg_stat_statements_reset();" >/dev/null
docker exec cinema_db_replica psql -U postgres -d kino -c "SELECT pg_stat_statements_reset();" >/dev/null 2>&1 || true

echo "==> 5/6 Regeneruje CSV-ki JMetera z aktualnych zakresow ID..."
python3 scripts/generate_perf_csvs.py >/dev/null

OUT="/tmp/jmeter_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"   
echo "==> 6/6 Start JMeter -> raport: ${OUT}/report/index.html"
echo "    PODGLAD NA ZYWO: Grafana http://localhost:3000  (dashboard 'Punkt zalamania')"


"$JMETER" -n -t tests/perf_test.jmx \
  -Jprometheus.ip=0.0.0.0 -Jprometheus.port=9270 \
  -l "${OUT}/results.jtl" -e -o "${OUT}/report" \
  -Jthreads="$THREADS" \
  -Jrampup="$RAMPUP" \
  -Jhold="$HOLD" \
  -Jshutdown="$SHUTDOWN" \
  -Jthink_offset="$THINK_OFFSET" \
  -Jthink_range="$THINK_RANGE"

echo "============================================================"
echo " GOTOWE. Raport HTML: ${OUT}/report/index.html"
echo " Wyniki surowe:       ${OUT}/results.jtl"
echo " W Grafanie ustaw zakres czasu na ostatnie ~15 min, by zobaczyc knee."
echo "============================================================"
