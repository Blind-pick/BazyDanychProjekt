FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client curl && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src
COPY ./scripts ./scripts

EXPOSE 8000


ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc


CMD sh -c '\
  until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do echo "Waiting for database..."; sleep 2; done && \
  rm -rf "$PROMETHEUS_MULTIPROC_DIR" && mkdir -p "$PROMETHEUS_MULTIPROC_DIR" && \
  echo "Database ready. Starting API with ${API_WORKERS:-4} uvicorn workers..." && \
  exec uvicorn src.main:app --host 0.0.0.0 --port 8000 \
       --workers "${API_WORKERS:-4}" --no-access-log --log-level warning \
       --timeout-keep-alive 30 --backlog 4096'
