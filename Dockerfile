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

CMD ["python3", "app.py"]
