from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
# Helper Function for Safe Access
# ----------------------------------------------------------------
def _get_profile_setting(user, setting_name, default=False):
    """
    Safely retrieves a setting from the user's profile.
    Returns default if profile does not exist.
    """
    if hasattr(user, 'profile'):
        return getattr(user.profile, setting_name, default)
    return default

def _get_profile_attr(user, attr_name, default=None):
    """
    Safely retrieves a string/value attribute from profile.
    """
    if hasattr(user, 'profile'):
        return getattr(user.profile, attr_name, default)
    return default


# ----------------------------------------------------------------
# Tasks
# ----------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_scheduled_reminders(self):
    """
    Send farming task reminders to users
    """
    try:
        from farming.models import FarmTask
        from accounts.models import User
        
        now = timezone.now()
        reminder_window = now + timedelta(hours=24)
        
        tasks = FarmTask.objects.select_related('farm', 'farm__owner').filter(
            due_date__range=(now, reminder_window),
            status='pending',
            reminder_sent=False
        )[:100]
        
        if not tasks:
            logger.info("No tasks requiring reminders")
            return {'sent': 0}
        
        sent_count = 0
        failed_count = 0
        
        user_tasks = {}
        for task in tasks:
            user = task.farm.owner
            if user.id not in user_tasks:
                user_tasks[user.id] = []
            user_tasks[user.id].append(task)
        
        for user_id, tasks_list in user_tasks.items():
            try:
                # Use select_related to fetch profile efficiently (if it exists)
                user = User.objects.select_related('profile').get(id=user_id)
                
                message = f"Farming Reminders ({len(tasks_list)}):\n"
                for task in tasks_list:
                    hours_until = (task.due_date - now).total_seconds() / 3600
                    message += f"- {task.title} (in {int(hours_until)}h)\n"
                
                # --- SAFE ACCESS IMPLEMENTED HERE ---
                sms_enabled = _get_profile_setting(user, 'sms_notifications')
                email_enabled = _get_profile_setting(user, 'email_notifications')
                
                if sms_enabled:
                    send_sms_notification.delay(user.phone_number, message) # type: ignore
                
                if email_enabled and user.email:
                    send_email_notification.delay(user.email, "Farming Reminders", message) # type: ignore
                
                # Mark as sent regardless of preference to avoid re-processing
                for task in tasks_list:
                    task.reminder_sent = True
                    task.save(update_fields=['reminder_sent'])
                
                sent_count += len(tasks_list)
                
            except Exception as e:
                logger.error(f"Failed to send reminders to user {user_id}: {str(e)}")
                failed_count += len(tasks_list)
        
        logger.info(f"Sent {sent_count} reminders, {failed_count} failed")
        return {'sent': sent_count, 'failed': failed_count}
    
    except Exception as e:
        logger.error(f"Error in send_scheduled_reminders: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def send_sms_notification(self, phone_number, message):
    """
    Send SMS notification via Africa's Talking
    """
    try:
        cache_key = f"sms_sent_{phone_number}_{hash(message)}"
        if cache.get(cache_key):
            logger.info(f"SMS duplicate skipped: {phone_number}")
            return {'status': 'skipped', 'reason': 'duplicate'}
        
        if not getattr(settings, 'ENABLE_NOTIFICATIONS', False):
            logger.info("Notifications disabled in settings")
            return {'status': 'disabled'}
        
        # Simulating External Service Call (Replace with real SDK)
        # import africastalking
        # ... logic ...
        
        cache.set(cache_key, True, 300)
        logger.info(f"SMS sent to {phone_number}")
        return {'status': 'sent', 'phone': phone_number}
    
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True, max_retries=3)
def send_email_notification(self, email, subject, message):
    """
    Send email notification
    """
    try:
        cache_key = f"email_sent_{email}_{hash(message)}"
        if cache.get(cache_key):
            return {'status': 'skipped', 'reason': 'duplicate'}
        
        if not getattr(settings, 'ENABLE_NOTIFICATIONS', False):
            return {'status': 'disabled'}
        
        from django.core.mail import send_mail
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        
        cache.set(cache_key, True, 300)
        return {'status': 'sent', 'email': email}
    
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        raise self.retry(exc=e, countdown=30)


@shared_task
def send_daily_farming_tips():
    """
    Send daily farming tips to active users
    """
    try:
        from accounts.models import User
        # from farming.ai_service import gemini_service (Assuming this exists)
        
        week_ago = timezone.now() - timedelta(days=7)
        
        # We cannot filter by 'profile__sms_notifications' effectively if profile is missing
        # So we get all active users and filter in python for safety
        active_users = User.objects.filter(
            last_login__gte=week_ago
        ).select_related('profile')[:500]
        
        tips_sent = 0
        
        for user in active_users:
            try:
                # --- SAFE ACCESS IMPLEMENTED HERE ---
                if not _get_profile_setting(user, 'sms_notifications'):
                    continue

                city = _get_profile_attr(user, 'city', 'Nigeria')
                experience = _get_profile_attr(user, 'experience_level', 'Beginner')
                farm_type = _get_profile_attr(user, 'farming_type', 'General')
                
                tip_data = {
                    'city': city,
                    'experience_level': experience,
                    'farming_type': farm_type
                }
                
                cache_key = f"daily_tip_{city}_{timezone.now().date()}"
                tip = cache.get(cache_key)
                
                if not tip:
                    # prompt = f"Quick farming tip for {experience} farmer in {city}"
                    # tip = gemini_service.answer_farming_question(prompt, context=tip_data)
                    tip = "Remember to check soil moisture today!" # Fallback simulation
                    cache.set(cache_key, tip, 86400)
                
                message = f"🌾 Daily Tip:\n{tip[:160]}"
                send_sms_notification.delay(user.phone_number, message) # type: ignore
                
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
    Send push notification
    """
    try:
        from accounts.models import User
        
        user = User.objects.select_related('profile').get(id=user_id)
        
        # --- SAFE ACCESS IMPLEMENTED HERE ---
        if not _get_profile_setting(user, 'push_notifications'):
            return {'status': 'disabled'}
        
        logger.info(f"Push notification to {user.phone_number}: {title}")
        return {'status': 'sent', 'user_id': user_id}
    
    except Exception as e:
        logger.error(f"Failed to send push notification: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def send_bulk_notifications(user_ids, message, notification_type='sms'):
    """
    Send bulk notifications efficiently
    """
    try:
        from accounts.models import User
        
        users = User.objects.filter(id__in=user_ids).select_related('profile')
        
        sent_count = 0
        failed_count = 0
        
        batch_size = 50
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]
            
            for user in batch:
                try:
                    # --- SAFE ACCESS IMPLEMENTED HERE ---
                    sms_enabled = _get_profile_setting(user, 'sms_notifications')
                    email_enabled = _get_profile_setting(user, 'email_notifications')

                    if notification_type == 'sms' and sms_enabled:
                        send_sms_notification.delay(user.phone_number, message) # type: ignore
                        sent_count += 1
                    
                    elif notification_type == 'email' and email_enabled:
                        send_email_notification.delay(user.email, "Notification", message) # type: ignore
                        sent_count += 1
                
                except Exception as e:
                    logger.error(f"Failed to send to user {user.id}: {str(e)}")
                    failed_count += 1
            
            import time
            time.sleep(1)
        
        return {'sent': sent_count, 'failed': failed_count}
    
    except Exception as e:
        logger.error(f"Error in send_bulk_notifications: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_old_notifications():
    """
    Clean up old notification records
    """
    try:
        from notifications.models import Notification
        
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