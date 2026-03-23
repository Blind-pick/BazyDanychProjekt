FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY ./db_interface/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./db_interface /app
COPY ./main.py /app/main.py
COPY ./CinemaDatabaseCreator.py /app/CinemaDatabaseCreator.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]