"""
AgroMentor 360 - Celery Configuration
Handles asynchronous tasks like notifications, reminders, and background processing
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrosphere.settings')

# Create Celery instance
app = Celery('agrosphere')

# Load configuration from Django settings with 'CELERY_' prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Celery Beat Schedule (Periodic Tasks)
app.conf.beat_schedule = {
    # Send farming reminders every hour
    'send-hourly-farming-reminders': {
        'task': 'notifications.tasks.send_scheduled_reminders',
        'schedule': crontab(minute=0),  # Every hour on the hour
    },
    
    # Update weather alerts every 6 hours
    'update-weather-forecasts': {
        'task': 'farming.tasks.update_weather_alerts',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
    
    # Check for matured investments daily at midnight
    'process-investment-returns': {
        'task': 'investments.tasks.process_matured_investments',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    
    # Send daily farming tips to users
    'send-daily-farming-tips': {
        'task': 'notifications.tasks.send_daily_farming_tips',
        'schedule': crontab(hour=7, minute=0),  # Daily at 7 AM
    },
    
    # Process pending expert consultations
    'process-consultation-reminders': {
        'task': 'experts.tasks.send_consultation_reminders',
        'schedule': crontab(hour='*/2'),  # Every 2 hours
    },
    
    # Update marketplace analytics
    'update-marketplace-analytics': {
        'task': 'analytics.tasks.update_marketplace_metrics',
        'schedule': crontab(hour='*/4'),  # Every 4 hours
    },
    
    # Clean up expired USSD sessions
    'cleanup-ussd-sessions': {
        'task': 'ussd.tasks.cleanup_expired_sessions',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    
    # Sync Ethereum transactions
    'sync-ethereum-transactions': {
        'task': 'blockchain.tasks.sync_pending_transactions',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}

# Celery Task Configuration
app.conf.update(
    # Task time limits
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    
    # Task retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Task routing (different queues for different task types)
    task_routes={
        'notifications.tasks.*': {'queue': 'notifications'},
        'blockchain.tasks.*': {'queue': 'blockchain'},
        'farming.tasks.*': {'queue': 'farming'},
        'analytics.tasks.*': {'queue': 'analytics'},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    
    # Timezone
    timezone='Africa/Lagos',
    enable_utc=True,
)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Debug task to test Celery configuration
    """
    print(f'Request: {self.request!r}')
    return 'Debug task executed successfully'

# Task error handler
@app.task(bind=True)
def error_handler(self, uuid):
    """
    Handle task errors and send notifications
    """
    result = self.app.AsyncResult(uuid)
    print(f'Task {uuid} raised exception: {result.traceback}')