# Multi-stage Docker build for SONiC NOS MCP Server with Quality Gates
# Stage 1: Quality Assurance - Code quality, type checking, and testing
FROM python:3.12-slim AS quality_gate

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock* README.md ./

# Create virtual environment with ALL dependencies (including dev dependencies)
RUN uv sync --frozen --no-cache

# Copy ALL source code and tests
COPY src/ ./src/
COPY test/ ./test/

# QUALITY GATE 1: Code formatting and linting with ruff
RUN echo "=== QUALITY GATE 1: Ruff Code Quality ===" \
    && uv run ruff format src/ test/ \
    && uv run ruff check src/ test/ \
    && echo "✅ Ruff quality checks passed"

# QUALITY GATE 2: Type checking with mypy
RUN echo "=== QUALITY GATE 2: MyPy Type Checking ===" \
    && uv run mypy src/ \
    && echo "✅ MyPy type checking passed"

# QUALITY GATE 3: All tests except evaluation must pass with 90%+ coverage
RUN echo "=== QUALITY GATE 3: All Tests with Coverage Validation ===" \
    && uv run python -m pytest test/unit/ test/integration/ -v --cov-report=term --cov-fail-under=90 \
    && echo "✅ All tests passed with required coverage (90%+)"

# Stage 2: Build clean production dependencies
FROM python:3.12-slim AS builder

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* README.md ./

# Create virtual environment with production dependencies only
RUN uv sync --frozen --no-dev --no-cache

# Copy source code (quality gates passed)
COPY src/ ./src/

# Stage 3: Minimal runtime image
FROM python:3.12-slim AS runtime

# Install minimal system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r mcpuser && useradd -r -g mcpuser -m mcpuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy source code from builder
COPY --from=builder /app/src ./src
COPY pyproject.toml ./

# Create temp directory with proper permissions
RUN mkdir -p /tmp/sonic-mcp \
    && chown -R mcpuser:mcpuser /app /tmp/sonic-mcp

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:${PYTHONPATH:-}"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER mcpuser

# Health check to ensure the server can import correctly
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sonic_nos_mcp.server; print('Server module loaded successfully')" || exit 1

# Default command to run the MCP server
ENTRYPOINT ["python", "-m", "sonic_nos_mcp.server"]
