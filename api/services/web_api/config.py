import os

from services.common.estabelecimentos import ESTABELECIMENTOS

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://tasy:tasy@localhost:5432/tasy_db")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

# Service do extractor usado para acionar a emissao/envio de nota por estabelecimento.
EXTRACTOR_URL = os.getenv("EXTRACTOR_URL", "http://localhost:8001")

# Processor (health / circuit breaker / stats).
PROCESSOR_URL = os.getenv("PROCESSOR_URL", "http://localhost:8002")

# RabbitMQ (consulta de profundidade das filas no painel).
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
RABBITMQ_QUEUE_RAW_NF = os.getenv("RABBITMQ_QUEUE_RAW_NF", "nf.raw")
RABBITMQ_QUEUE_DEAD = os.getenv("RABBITMQ_QUEUE_DEAD", "nf.dead")

# URL do report-service (disparo manual de e-mail).
REPORT_URL = os.getenv("REPORT_URL", "http://localhost:8004")

# Credenciais do administrador inicial criado no startup (seed).
BOOTSTRAP_ADMIN_USERNAME = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "admin123")

# Usuario dev opcional (auditoria de acessos + filas). Vazio = nao cria no seed.
BOOTSTRAP_DEV_USERNAME = os.getenv("BOOTSTRAP_DEV_USERNAME", "").strip()
BOOTSTRAP_DEV_PASSWORD = os.getenv("BOOTSTRAP_DEV_PASSWORD", "").strip()
BOOTSTRAP_DEV_EMAIL = os.getenv("BOOTSTRAP_DEV_EMAIL", "").strip() or None

# CORS: origens permitidas do frontend (separadas por virgula).
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
