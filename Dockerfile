# TensorFlow 2.21 publishes no 3.14 wheels, so this must track render.yaml /
# runtime.txt at 3.12.
FROM python:3.12-slim
WORKDIR /app

# Build args
ARG INSTALL_ML=0

# Install system deps. No compiler is needed: every pip install below is
# --only-binary, and npm runs with --ignore-scripts.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# requirements*.lock.txt are generated from uv.lock and carry pinned versions
# plus hashes for every transitive dependency, so --require-hashes can verify
# the whole tree. Regenerate with `uv export` (see CONTRIBUTING.md).
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir --require-hashes --only-binary :all: \
    -r requirements.lock.txt

# Optionally install heavy ML dependencies at build time
COPY requirements-ml.lock.txt ./
RUN if [ "${INSTALL_ML}" = "1" ]; then \
    pip install --no-cache-dir --require-hashes --only-binary :all: \
    -r requirements-ml.lock.txt; \
    fi

COPY . .

# Build client if present, then create non-root user
RUN if [ -d "./client" ]; then \
    cd client && npm ci --ignore-scripts && npm run build && cd ..; \
    fi && \
    useradd --create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
