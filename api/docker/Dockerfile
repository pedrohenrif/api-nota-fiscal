FROM python:3.11-slim
WORKDIR /app

# libaio e dependencia do Oracle Instant Client (modo thick).
# Debian Trixie usa libaio1t64; Bookworm usa libaio1.
# Instant Client vem montado da VM via docker-compose.
RUN apt-get update \
    && (apt-get install -y --no-install-recommends libaio1t64 \
        || apt-get install -y --no-install-recommends libaio1) \
    && if [ ! -e /usr/lib/x86_64-linux-gnu/libaio.so.1 ] \
          && [ -e /usr/lib/x86_64-linux-gnu/libaio.so.1t64 ]; then \
         ln -s libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1; \
       fi \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

CMD ["uvicorn", "services.extractor.main:app", "--host", "0.0.0.0", "--port", "8001"]
