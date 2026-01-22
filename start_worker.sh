#!/bin/bash

# Runs Celery worker for all queues
celery -A agrosphere worker -Q notifications,blockchain,analytics,investments,experts,celery -l info &

# Start Django server (for demo)
python manage.py runserver 0.0.0.0:8000