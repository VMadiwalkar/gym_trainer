FROM python:3.12-slim


COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock ./


RUN uv sync --frozen 
EXPOSE 5000

COPY . .

CMD ["python", "app.py"]
