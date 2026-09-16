# Multi-Stage Dockerfile for TunnelFlare Hybrid Web Mesh
# Stage 1: Build React/Vite Frontend
FROM node:22-slim AS frontend-builder
WORKDIR /app/web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# Stage 2: Runtime Environment with cloudflared & Python FastAPI
FROM python:3.12-slim-bookworm AS runner

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies, iptables, and cloudflared
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    iptables \
    iproute2 \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install cloudflared
RUN arch=$(dpkg --print-architecture) && \
    wget -q -O /usr/local/bin/cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${arch}" && \
    chmod +x /usr/local/bin/cloudflared

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt httpx

# Copy application files
COPY main.py tui.py utils.py cloudflare_api.py web_server.py ./
COPY resources ./resources

# Copy compiled frontend from Stage 1
COPY --from=frontend-builder /app/web/dist ./web/dist

EXPOSE 8080

ENTRYPOINT ["python3", "main.py"]
CMD ["web", "--host", "0.0.0.0", "--port", "8080"]
