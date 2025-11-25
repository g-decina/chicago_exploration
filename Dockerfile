FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

COPY . .

ENV PYTHONPATH=/code
RUN chmod +x scripts/*.sh

CMD ["./scripts/start_backend.sh"]