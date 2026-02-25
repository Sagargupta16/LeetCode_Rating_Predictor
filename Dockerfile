FROM python:3.12-slim
WORKDIR /app

# Build args
ARG INSTALL_ML=0

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Optionally install heavy ML dependencies at build time
COPY requirements-ml.txt ./
RUN if [ "${INSTALL_ML}" = "1" ]; then \
    pip install --no-cache-dir -r requirements-ml.txt; \
    fi

COPY . .

# Build client if present, then create non-root user
RUN if [ -d "./client" ]; then \
    cd client && npm ci && npm run build && cd ..; \
    fi && \
    useradd --create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
