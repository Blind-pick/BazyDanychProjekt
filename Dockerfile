FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY ./requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./src ./src
COPY ./scripts ./scripts

EXPOSE 8000

CMD sh -c 'until pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER; do echo "Waiting for database..."; sleep 2; done && echo "Database ready. Starting API..." && exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --log-level info'