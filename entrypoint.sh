#!/bin/sh
set -e

echo "Выполняем миграции..."
python /app/src/manage.py migrate

echo "Собираем статические файлы..."
python /app/src/manage.py collectstatic --noinput

echo "Запускаем Gunicorn..."
exec gunicorn diploma_smart_parking.wsgi:application \
    --bind 0.0.0.0:8002 \
    --workers 3
