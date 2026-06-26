FROM python:3.11-slim
WORKDIR /app

# Oracle Instant Client (modo thick) — exigido pelo Tasy homolog (criptografia nativa)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libaio1 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

ENV ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient_21_15
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_21_15

RUN mkdir -p /opt/oracle \
    && wget -q \
        https://download.oracle.com/otn_software/linux/instantclient/2115000/instantclient-basiclite-linux.x64-21.15.0.0.0dbru.zip \
        -O /tmp/instantclient.zip \
    && unzip -q /tmp/instantclient.zip -d /opt/oracle \
    && rm /tmp/instantclient.zip

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

CMD ["uvicorn", "services.extractor.main:app", "--host", "0.0.0.0", "--port", "8001"]
