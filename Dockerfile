FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

RUN mkdir -p /var/data/data

ENV DATA_DIR=/var/data/data
ENV VECTOR_DB=/var/data/vector_store.sqlite3
ENV GENERATED_PROJECTS_DIR=/var/data/generated_projects
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
