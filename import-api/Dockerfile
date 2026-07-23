FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY dpp_aas ./dpp_aas
COPY data/templates ./data/templates
COPY data/assets ./data/assets
COPY import-api/requirements.txt ./import-api/requirements.txt

RUN pip install --no-cache-dir . -r import-api/requirements.txt \
    && useradd --create-home --uid 10001 importer

COPY import-api/main.py ./import_api.py

USER importer
EXPOSE 8000

CMD ["uvicorn", "import_api:app", "--host", "0.0.0.0", "--port", "8000"]
