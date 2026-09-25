# ============================================================
# VietDub Auto — Dockerfile
# Multi-stage build: nhỏ gọn, production-ready
# ============================================================

# === Stage 1: Builder ===
FROM python:3.11-slim AS builder

WORKDIR /app

# Cài system deps cần để build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements trước (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# === Stage 2: Runtime ===
FROM python:3.11-slim AS runtime

WORKDIR /app

# Cài FFmpeg (bắt buộc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages từ builder
COPY --from=builder /root/.local /root/.local

# Copy source code
COPY backend/ ./backend/
COPY .env.example .env.example

# Tạo thư mục output
RUN mkdir -p output

# Cấu hình PATH
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Mặc định chạy API server
CMD ["python", "backend/api/server.py"]
