FROM mcr.microsoft.com/playwright/python:v1.59.0-jammy

WORKDIR /app

RUN pip install --no-cache-dir uv==0.5.11

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY app ./app
COPY templates ./templates
COPY static ./static

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
