FROM python:3.14-slim
WORKDIR /app

# Build args
ARG INSTALL_ML=0

# Install system deps
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Optionally install heavy ML dependencies at build time
COPY requirements-ml.txt ./
RUN if [ "${INSTALL_ML}" = "1" ]; then \
    pip install --no-cache-dir -r requirements-ml.txt; \
    fi

COPY . .

# Build client if present
RUN if [ -d "./client" ]; then \
    cd client && npm ci --silent && npm run build --silent && cd ..; \
    fi

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
