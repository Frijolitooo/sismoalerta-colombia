FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY frontend frontend
WORKDIR /app/backend
RUN mkdir -p data models
ENV DB_PATH=data/sismoalerta.db BACKFILL_DAYS=365
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
