FROM python:3.11.18-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_CONCURRENT_DOWNLOADS=4 \
    UV_HTTP_TIMEOUT=120 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT="/opt/venv" \
    PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

EXPOSE 8000
CMD ["uvicorn", "src.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]