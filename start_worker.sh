#!/bin/bash

# Runs ONE worker that checks all 3 queues
# It checks them in order: billing first, then notifications, then default
celery -A core worker -Q notifications,blockchain,analytics,investments,experts,celery -l info &

# Dummy server
python -m http.server $PORT