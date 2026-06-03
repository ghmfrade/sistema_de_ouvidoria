FROM python:3.13-slim

WORKDIR /app

# Instala deps Python (camada cacheada)
COPY qualidade_dash/requirements.txt ./qualidade_dash/requirements.txt
RUN pip install --no-cache-dir -r qualidade_dash/requirements.txt

# Copia codigo (qualidade_dash e totalmente autocontido)
COPY qualidade_dash/ ./qualidade_dash/

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8050

# Em prod, gunicorn no lugar do servidor de dev do Dash
CMD ["gunicorn", \
     "--bind=0.0.0.0:8050", \
     "--workers=2", \
     "--access-logfile=-", \
     "qualidade_dash.app:server"]
