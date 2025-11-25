# 1. BUILD
FROM python:3.12-slim as builder

ENV PYTHONUNBUFFERED=1

WORKDIR /install

# Install dependencies in a separate dir
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt --target=/usr/local/lib/python3.12/site-packages

# 2. RUNTIME IMAGE
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /code

# Copy install packages from step 1
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy source code
COPY . .

ENV PYTHONPATH=/code

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]