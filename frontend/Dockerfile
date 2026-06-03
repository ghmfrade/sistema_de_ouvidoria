FROM python:3.13-slim

WORKDIR /app

# Instala deps Python (camada cacheada)
COPY frontend/requirements.txt ./frontend/requirements.txt
RUN pip install --no-cache-dir -r frontend/requirements.txt

# Copia codigo do frontend + dependencias compartilhadas
COPY frontend/ ./frontend/
COPY utils/ ./utils/
# api/client/ e nada mais de api/ — frontend so usa o HTTP client SDK
COPY api/__init__.py ./api/__init__.py
COPY api/client/ ./api/client/

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8501

CMD ["streamlit", "run", "frontend/app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]