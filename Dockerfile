# 1. BUILD
FROM python:3.12-slim as builder

ENV PYTHONUNBUFFERED=1

WORKDIR /install

# Install dependencies in a separate dir
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 2. RUNTIME IMAGE
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /code

# Copy install packages from step 1
COPY --from=builder /install /usr/local

# Copy source code
COPY . .

ENV PYTHONPATH=/code

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]