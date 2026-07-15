# Stage 1: Build Python dependencies
FROM python:3.12-alpine AS builder

WORKDIR /build

COPY backend/requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Minimal runtime
FROM alpine:3.20

RUN apk add --no-cache python3 ca-certificates

WORKDIR /app

COPY --from=builder /install/lib/python3.12/site-packages /usr/lib/python3.12/site-packages
COPY --from=builder /install/bin /usr/local/bin

COPY backend/app.py .
COPY frontend/ /app/frontend/

RUN mkdir -p /data

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["python3", "app.py"]
