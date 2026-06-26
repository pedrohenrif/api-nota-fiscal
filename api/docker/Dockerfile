FROM python:3.11-slim
WORKDIR /app

# libaio1 e necessario para o modo thick; Instant Client vem montado da VM via docker-compose
RUN apt-get update && apt-get install -y --no-install-recommends libaio1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

CMD ["uvicorn", "services.extractor.main:app", "--host", "0.0.0.0", "--port", "8001"]
