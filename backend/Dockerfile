FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# docker-compose overrides this CMD with --reload for local dev; this is
# the sane default for a standalone `docker build && docker run`.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
