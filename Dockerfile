# PyEdgeTwin Docker Image
# Multi-stage build for minimal production image

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir build wheel

# Copy source files
COPY pyproject.toml README.md ./
COPY src/ src/

# Build wheel
RUN python -m build --wheel --outdir /app/dist

# Stage 2: Production
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install the wheel from builder stage
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Create config directory
RUN mkdir -p /home/appuser/config

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Expose health endpoint port
EXPOSE 8080

# Default entrypoint
ENTRYPOINT ["pyedgetwin"]
CMD ["run", "-c", "/config/config.yaml"]
