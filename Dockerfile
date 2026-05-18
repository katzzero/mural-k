FROM alpine:3.20

RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-virtualenv \
    && rm -rf /var/cache/apk/*

WORKDIR /app

RUN python3 -m virtualenv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY frontend/ /app/frontend/

RUN mkdir -p /data

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:5000/health || exit 1

CMD ["python3", "app.py"]
