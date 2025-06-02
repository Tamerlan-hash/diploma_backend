# =====================
# 1. Стадия сборки
# =====================
FROM python:3.11-slim AS builder

WORKDIR /app

# Установка Poetry
RUN pip install poetry==2.1.0
# Указываем, чтобы venv создавался в /app/.venv
RUN poetry config virtualenvs.in-project true

# Копируем файлы для установки зависимостей
COPY pyproject.toml poetry.lock ./

# Устанавливаем зависимости (без запуска кода)
RUN poetry install --no-root

# Копируем весь исходный код (включая manage.py)
COPY src/ src/
COPY README.md README.md

# Дополнительная установка зависимостей на основе локального кода (если нужно)
RUN poetry install

# ======================
# 2. Финальный образ
# ======================
FROM python:3.11-slim AS api

WORKDIR /app

# Копируем готовое окружение из builder
COPY --from=builder /app/.venv /app/.venv

# Прописываем PATH, чтобы python/gunicorn/etc. были доступны без полного пути
ENV PATH="/app/.venv/bin:$PATH"

# Копируем исходный код
COPY --from=builder /app/src /app/src

# Копируем скрипт entrypoint и даём ему права
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# При запуске контейнера исполняется entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
