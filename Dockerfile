# ---- Build stage ----
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime stage ----
FROM python:3.12-slim
WORKDIR /app
# Patch zlib1g until the base image ships the Debian security fix; remove this step then.
RUN apt-get update \
 && apt-get install -y --no-install-recommends --only-upgrade zlib1g \
 && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app
COPY --from=builder /install /usr/local
COPY . .
RUN mkdir -p /app/instance && chown app:app /app/instance
USER 10001:10001
EXPOSE 5000
CMD ["python3", "app.py"]
