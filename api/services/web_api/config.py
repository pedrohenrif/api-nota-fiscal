import os


POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://tasy:tasy@localhost:5432/tasy_db")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

# Service do extractor usado para acionar a emissao/envio de nota por estabelecimento.
EXTRACTOR_URL = os.getenv("EXTRACTOR_URL", "http://localhost:8001")

# Credenciais do administrador inicial criado no startup (seed).
BOOTSTRAP_ADMIN_USERNAME = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "admin123")

# CORS: origens permitidas do frontend (separadas por virgula).
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

ESTABELECIMENTOS = ["Castelo", "HRAS", "HRT", "Ponta Pora"]
