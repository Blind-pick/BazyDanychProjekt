#!/usr/bin/env bash
#
# Kompletny przebieg testu obciazeniowego "progressive overload".
#
# Co robi:
#   1. Zaciska DB do waskiego gardla (domyslnie 1 CPU / 1 GB).
#   2. Restartuje API (swieza pula polaczen).
#   3. RESETUJE pg_stat_statements - liczniki zaczynaja od zera, wiec w Grafanie
#      nie widac juz INSERT-ow z ladowania ani operacji na indeksach/FK.
#   4. Regeneruje CSV-ki JMetera z aktualnych zakresow ID.
#   5. Odpala JMeter ze STEPPING THREAD GROUP - obciazenie rosnie schodkowo.
#
# Uzycie (z katalogu projektu):
#   bash scripts/run_stress_test.sh
#
# Strojenie przez zmienne srodowiskowe, np. lagodniej i dluzej:
#   THREADS=200 STEP_USERS=20 STEP_PERIOD=20 HOLD=120 bash scripts/run_stress_test.sh
#   DB_CPUS=0.5 DB_MEMORY=512m bash scripts/run_stress_test.sh   # slabsza baza
#
set -euo pipefail
cd "$(dirname "$0")/.."

# --- Parametry (nadpisywalne env) ---
DB_CPUS="${DB_CPUS:-1}"
DB_MEMORY="${DB_MEMORY:-1g}"
THREADS="${THREADS:-300}"        # docelowa liczba watkow (szczyt)
STEP_USERS="${STEP_USERS:-25}"   # ile watkow dokladamy na schodek
STEP_PERIOD="${STEP_PERIOD:-30}" # co ile sekund kolejny schodek
STEP_RAMP="${STEP_RAMP:-5}"      # narastanie watkow w obrebie schodka
HOLD="${HOLD:-180}"              # ile trzymac pelne obciazenie po szczycie

# --- Lokalizacja JMetera ---
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

steps=$(( (THREADS + STEP_USERS - 1) / STEP_USERS ))
echo "============================================================"
echo " PROGRESSIVE OVERLOAD"
echo "   DB limit:    ${DB_CPUS} CPU / ${DB_MEMORY}"
echo "   Schodki:     +${STEP_USERS} watkow co ${STEP_PERIOD}s -> ${THREADS} watkow"
echo "   Narastanie:  ${steps} schodkow x ${STEP_PERIOD}s = $(( steps * STEP_PERIOD ))s"
echo "   Hold:        ${HOLD}s na szczycie"
echo "   JMeter:      ${JMETER}"
echo "============================================================"

echo "==> 1/4 Zaciskam DB do ${DB_CPUS} CPU / ${DB_MEMORY}..."
DB_CPUS="$DB_CPUS" DB_MEMORY="$DB_MEMORY" docker compose up -d db
until docker inspect cinema_db --format '{{.State.Health.Status}}' 2>/dev/null | grep -q healthy; do sleep 2; done

echo "==> 2/4 Swiezy restart API (pula polaczen musi sie odtworzyc po recreate DB)..."
# force-recreate: po kazdym recreate kontenera DB pula psycopg trzyma martwe
# polaczenia do starego IP i sama sie nie podnosi - dlatego zawsze startujemy api od nowa.
docker compose up -d --force-recreate api >/dev/null
until curl -sf localhost:8000/health >/dev/null 2>&1; do sleep 2; done
echo "==> Reset pg_stat_statements (czyste liczniki na czas testu)..."
docker exec cinema_db psql -U postgres -d kino -c "SELECT pg_stat_statements_reset();" >/dev/null

echo "==> 3/4 Regeneruje CSV-ki JMetera..."
python3 scripts/generate_perf_csvs.py >/dev/null

OUT="/tmp/jmeter_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"   # JMeter wymaga istniejacego katalogu na wyniki (raport tworzy sam)
echo "==> 4/4 Start JMeter -> raport: ${OUT}/report/index.html"
echo "    (podglad na zywo: Grafana http://localhost:3000)"
"$JMETER" -n -t tests/perf_test.jmx \
  -l "${OUT}/results.jtl" -e -o "${OUT}/report" \
  -Jthreads="$THREADS" \
  -Jstep_users="$STEP_USERS" \
  -Jstep_period="$STEP_PERIOD" \
  -Jstep_ramp="$STEP_RAMP" \
  -Jhold="$HOLD"

echo "============================================================"
echo " GOTOWE. Raport HTML: ${OUT}/report/index.html"
echo " Wyniki surowe:       ${OUT}/results.jtl"
echo "============================================================"
