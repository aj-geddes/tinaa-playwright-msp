# =============================================================================
# Stage 1: builder
# Install Python dependencies into a virtual environment for clean copying.
# =============================================================================
FROM mcr.microsoft.com/playwright/python:v1.46.1-jammy AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VENV_PATH=/opt/venv

RUN python3 -m venv $VENV_PATH
ENV PATH="$VENV_PATH/bin:$PATH"

# Upgrade pip once in the venv
RUN pip install --upgrade pip

# Copy dependency declarations first — this layer is cached until they change.
WORKDIR /build
COPY pyproject.toml ./
# Install production dependencies only (no [dev] extras)
RUN pip install .

# =============================================================================
# Stage 2: development
# Inherits the builder venv, adds the source tree, and runs with hot-reload.
# Used only via docker-compose.dev.yml (target: development).
# =============================================================================
FROM mcr.microsoft.com/playwright/python:v1.46.1-jammy AS development

LABEL org.opencontainers.image.title="TINAA MSP (dev)" \
      org.opencontainers.image.version="2.0.0" \
      org.opencontainers.image.description="TINAA MSP development image with hot reload"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VENV_PATH=/opt/venv \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    TINAA_MODE=api

ENV PATH="$VENV_PATH/bin:$PATH"

# Copy the venv from builder
COPY --from=builder /opt/venv /opt/venv

# Install Playwright browsers (chromium only — minimise image size)
RUN playwright install chromium --with-deps

WORKDIR /app

# In dev mode the source is bind-mounted; create the directory structure so
# the container starts cleanly even before the mount lands.
RUN mkdir -p /app/logs

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

# Dev runs as root so that bind-mounted files owned by the host user are
# always writable. This is intentional and acceptable for dev-only images.
CMD ["uvicorn", "tinaa.api.app:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8765", "--reload"]

# =============================================================================
# Stage 3: production
# Minimal runtime — no build tools, non-root user, read-only-friendly.
# =============================================================================
FROM mcr.microsoft.com/playwright/python:v1.46.1-jammy AS production

LABEL org.opencontainers.image.title="TINAA MSP" \
      org.opencontainers.image.version="2.0.0" \
      org.opencontainers.image.description="TINAA MSP — Testing Intelligence Network Automation Assistant" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VENV_PATH=/opt/venv \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    TINAA_MODE=api

ENV PATH="$VENV_PATH/bin:$PATH"

# Copy the venv from builder
COPY --from=builder /opt/venv /opt/venv

# Install Playwright browsers (chromium only)
RUN playwright install chromium --with-deps

# Create a non-root user for the runtime process
RUN groupadd -g 1001 tinaa && \
    useradd -u 1001 -g tinaa -m -s /bin/bash tinaa && \
    mkdir -p /app/logs && \
    chown -R tinaa:tinaa /app /ms-playwright

WORKDIR /app

# Copy application source — code changes do NOT invalidate the dependency layer
COPY --chown=tinaa:tinaa tinaa/ ./tinaa/

USER tinaa

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

# Entrypoint script honours TINAA_MODE:
#   TINAA_MODE=mcp  -> runs the FastMCP stdio server
#   TINAA_MODE=api  -> runs the FastAPI HTTP server (default)
COPY --chown=tinaa:tinaa scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
