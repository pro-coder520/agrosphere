#!/bin/bash

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start Celery Beat in background
celery -A agrosphere beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &

# Start Celery Worker in background
celery -A agrosphere worker -Q notifications,blockchain,analytics,investments,experts,celery -l info &

# Start Gunicorn
gunicorn agrosphere.wsgi:application --bind 0.0.0.0:10000 --workers 2 --timeout 120