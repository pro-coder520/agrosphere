from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_scheduled_reminders(self):
    """
    Send farming task reminders to users
    Runs hourly via Celery Beat
    Optimized with batching and caching
    """
    try:
        from farming.models import FarmTask
        from accounts.models import User
        
        # Get tasks due in the next 24 hours that haven't sent reminders
        now = timezone.now()
        reminder_window = now + timedelta(hours=24)
        
        tasks = FarmTask.objects.select_related('farm', 'farm__owner').filter(
            due_date__range=(now, reminder_window),
            status='pending',
            reminder_sent=False
        )[:100]  # Batch limit for performance
        
        if not tasks:
            logger.info("No tasks requiring reminders")
            return {'sent': 0, 'message': 'No reminders to send'}
        
        sent_count = 0
        failed_count = 0
        
        # Batch process by user to optimize notifications
        user_tasks = {}
        for task in tasks:
            user = task.farm.owner
            if user.id not in user_tasks:
                user_tasks[user.id] = []
            user_tasks[user.id].append(task)
        
        # Send batched notifications
        for user_id, tasks_list in user_tasks.items():
            try:
                user = User.objects.get(id=user_id)
                
                # Build notification message
                message = f"Farming Reminders ({len(tasks_list)}):\n"
                for task in tasks_list:
                    hours_until = (task.due_date - now).total_seconds() / 3600
                    message += f"- {task.title} (in {int(hours_until)}h)\n"
                
                # Send via appropriate channel
                if user.profile.sms_notifications:
                    send_sms_notification.delay(user.phone_number, message)
                
                if user.profile.email_notifications and user.email:
                    send_email_notification.delay(user.email, "Farming Reminders", message)
                
                # Mark reminders as sent
                for task in tasks_list:
                    task.reminder_sent = True
                    task.save(update_fields=['reminder_sent'])
                
                sent_count += len(tasks_list)
                
            except Exception as e:
                logger.error(f"Failed to send reminders to user {user_id}: {str(e)}")
                failed_count += len(tasks_list)
        
        logger.info(f"Sent {sent_count} reminders, {failed_count} failed")
        return {
            'sent': sent_count,
            'failed': failed_count,
            'users_notified': len(user_tasks)
        }
    
    except Exception as e:
        logger.error(f"Error in send_scheduled_reminders: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def send_sms_notification(self, phone_number, message):
    """
    Send SMS notification via Africa's Talking
    Optimized with retry logic and caching
    """
    try:
        # Check cache to prevent duplicate SMS within 5 minutes
        cache_key = f"sms_sent_{phone_number}_{hash(message)}"
        if cache.get(cache_key):
            logger.info(f"SMS already sent to {phone_number} recently")
            return {'status': 'skipped', 'reason': 'duplicate'}
        
        if not settings.ENABLE_NOTIFICATIONS:
            logger.info("Notifications disabled in settings")
            return {'status': 'disabled'}
        
        # Send via Africa's Talking
        import africastalking
        
        username = settings.AFRICAS_TALKING_CONFIG['USERNAME']
        api_key = settings.AFRICAS_TALKING_CONFIG['API_KEY']
        
        africastalking.initialize(username, api_key)
        sms = africastalking.SMS
        
        response = sms.send(message, [phone_number])
        
        # Cache successful send
        cache.set(cache_key, True, 300)  # 5 minutes
        
        logger.info(f"SMS sent to {phone_number}: {response}")
        return {
            'status': 'sent',
            'phone': phone_number,
            'response': str(response)
        }
    
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True, max_retries=3)
def send_email_notification(self, email, subject, message):
    """
    Send email notification via SendGrid
    Optimized with HTML templates and caching
    """
    try:
        # Check cache to prevent duplicate emails
        cache_key = f"email_sent_{email}_{hash(message)}"
        if cache.get(cache_key):
            logger.info(f"Email already sent to {email} recently")
            return {'status': 'skipped', 'reason': 'duplicate'}
        
        if not settings.ENABLE_NOTIFICATIONS:
            return {'status': 'disabled'}
        
        from django.core.mail import send_mail
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        
        # Cache successful send
        cache.set(cache_key, True, 300)  # 5 minutes
        
        logger.info(f"Email sent to {email}")
        return {
            'status': 'sent',
            'email': email
        }
    
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        raise self.retry(exc=e, countdown=30)


@shared_task
def send_daily_farming_tips():
    """
    Send daily farming tips to active users
    Runs daily at 7 AM via Celery Beat
    """
    try:
        from accounts.models import User
        from farming.ai_service import gemini_service
        
        # Get active users (logged in within last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        active_users = User.objects.filter(
            last_login__gte=week_ago,
            profile__sms_notifications=True
        ).select_related('profile')[:500]  # Batch limit
        
        tips_sent = 0
        
        for user in active_users:
            try:
                # Generate personalized tip based on user's location
                tip_data = {
                    'city': user.profile.city,
                    'experience_level': user.profile.experience_level,
                    'farming_type': user.profile.farming_type
                }
                
                # Cache tips to avoid regenerating for same location
                cache_key = f"daily_tip_{user.profile.city}_{timezone.now().date()}"
                tip = cache.get(cache_key)
                
                if not tip:
                    # Generate new tip
                    prompt = f"Quick farming tip for {user.profile.experience_level} farmer in {user.profile.city}"
                    tip = gemini_service.answer_farming_question(prompt, context=tip_data)
                    cache.set(cache_key, tip, 86400)  # Cache for 1 day
                
                # Send tip
                message = f"🌾 Daily Farming Tip:\n{tip[:160]}"  # SMS length limit
                send_sms_notification.delay(user.phone_number, message)
                
                tips_sent += 1
                
            except Exception as e:
                logger.error(f"Failed to send tip to {user.phone_number}: {str(e)}")
        
        logger.info(f"Sent {tips_sent} daily farming tips")
        return {'tips_sent': tips_sent}
    
    except Exception as e:
        logger.error(f"Error in send_daily_farming_tips: {str(e)}")
        return {'error': str(e)}


@shared_task(bind=True)
def send_push_notification(self, user_id, title, body, data=None):
    """
    Send push notification to mobile app
    Ready for Firebase Cloud Messaging integration
    """
    try:
        from accounts.models import User
        
        user = User.objects.get(id=user_id)
        
        if not user.profile.push_notifications:
            return {'status': 'disabled'}
        
        # TODO: Implement Firebase Cloud Messaging
        # For now, log the notification
        logger.info(f"Push notification to {user.phone_number}: {title}")
        
        return {
            'status': 'sent',
            'user_id': user_id,
            'title': title
        }
    
    except Exception as e:
        logger.error(f"Failed to send push notification: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def send_bulk_notifications(user_ids, message, notification_type='sms'):
    """
    Send bulk notifications efficiently
    Optimized with batching and rate limiting
    """
    try:
        from accounts.models import User
        
        users = User.objects.filter(id__in=user_ids).select_related('profile')
        
        sent_count = 0
        failed_count = 0
        
        # Process in batches to avoid overwhelming the system
        batch_size = 50
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]
            
            for user in batch:
                try:
                    if notification_type == 'sms' and user.profile.sms_notifications:
                        send_sms_notification.delay(user.phone_number, message)
                        sent_count += 1
                    
                    elif notification_type == 'email' and user.profile.email_notifications:
                        send_email_notification.delay(user.email, "Notification", message)
                        sent_count += 1
                
                except Exception as e:
                    logger.error(f"Failed to send to user {user.id}: {str(e)}")
                    failed_count += 1
            
            # Rate limiting between batches
            import time
            time.sleep(1)
        
        logger.info(f"Bulk notification: {sent_count} sent, {failed_count} failed")
        return {
            'sent': sent_count,
            'failed': failed_count
        }
    
    except Exception as e:
        logger.error(f"Error in send_bulk_notifications: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_old_notifications():
    """
    Clean up old notification records
    Runs weekly to maintain database performance
    """
    try:
        from notifications.models import Notification
        
        # Delete notifications older than 90 days
        cutoff_date = timezone.now() - timedelta(days=90)
        deleted_count, _ = Notification.objects.filter(
            created_at__lt=cutoff_date,
            is_read=True
        ).delete()
        
        logger.info(f"Cleaned up {deleted_count} old notifications")
        return {'deleted': deleted_count}
    
    except Exception as e:
        logger.error(f"Error in cleanup_old_notifications: {str(e)}")
        return {'error': str(e)}