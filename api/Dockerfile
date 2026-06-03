FROM python:3.13-slim

WORKDIR /app

# System deps: gcc para psycopg2, libpq para PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala deps Python (camada cacheada separadamente do codigo)
COPY api/requirements.txt ./api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

# Copia codigo (api/ + utils/ compartilhado)
COPY api/ ./api/
COPY utils/ ./utils/

# Cria diretorio de uploads (sera sobreposto por volume em runtime)
RUN mkdir -p /data/uploads

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    UPLOADS_DIR=/data/uploads

EXPOSE 8000

# Aplica migrations e sobe o uvicorn
CMD ["sh", "-c", "cd /app/api && alembic upgrade head && cd /app && uvicorn api.main:app --host 0.0.0.0 --port 8000"]
