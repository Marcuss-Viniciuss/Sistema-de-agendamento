FROM python:3.12-slim

# Não gera .pyc e mostra logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/agendamentos.db

WORKDIR /code

# Copia só o requirements primeiro: o Docker reaproveita esta camada em cache
# enquanto as dependências não mudarem
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Utilizador sem privilégios + pasta onde o SQLite guarda os dados
RUN useradd --create-home appuser \
    && mkdir /data \
    && chown appuser /data
USER appuser

VOLUME /data
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
