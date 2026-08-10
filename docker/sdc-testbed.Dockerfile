FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config

RUN python -m pip install --no-cache-dir ".[sdc]"

ENTRYPOINT ["python", "-m"]
