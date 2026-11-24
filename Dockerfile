FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

COPY alembic.ini ./
COPY migrations ./migrations
COPY data/snapshot ./data/snapshot

RUN useradd --create-home app
USER app
EXPOSE 8000

# Migrate, load the committed snapshot (one transaction, safe to repeat), then serve.
CMD ["sh", "-c", "alembic upgrade head && zod load && uvicorn zod.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
