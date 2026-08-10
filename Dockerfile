# Runtime needs no ML framework, so the base image only has to carry numpy and
# the web stack. Kept at 3.12 to match render.yaml / runtime.txt.
FROM python:3.12-slim
WORKDIR /app

# Install system deps. No compiler is needed: the pip install below is
# --only-binary, and npm runs with --ignore-scripts.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# requirements.lock.txt is generated from uv.lock and carries pinned versions
# plus hashes for every transitive dependency, so --require-hashes can verify
# the whole tree. Regenerate with `uv export` (see CONTRIBUTING.md).
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir --require-hashes --only-binary :all: \
    -r requirements.lock.txt

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
