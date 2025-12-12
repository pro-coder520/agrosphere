from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_consultation_reminders():
    """
    Send reminders for upcoming consultations
    Runs every 2 hours via Celery Beat
    """
    try:
        from experts.models import Consultation
        from notifications.tasks import send_sms_notification
        
        # Get consultations in the next 24 hours
        now = timezone.now()
        tomorrow = now + timedelta(hours=24)
        
        upcoming = Consultation.objects.filter(
            scheduled_time__range=(now, tomorrow),
            status='confirmed',
            reminder_sent=False
        ).select_related('farmer', 'expert')
        
        reminders_sent = 0
        
        for consultation in upcoming:
            hours_until = (consultation.scheduled_time - now).total_seconds() / 3600
            
            # Send reminder to farmer
            farmer_message = (
                f"Reminder: Consultation with {consultation.expert.get_full_name()} "
                f"in {int(hours_until)} hours. Topic: {consultation.topic}"
            )
            send_sms_notification.delay(consultation.farmer.phone_number, farmer_message) #type:ignore
            
            # Send reminder to expert
            expert_message = (
                f"Reminder: Consultation with {consultation.farmer.get_full_name()} "
                f"in {int(hours_until)} hours. Topic: {consultation.topic}"
            )
            send_sms_notification.delay(consultation.expert.phone_number, expert_message) #type:ignore
            
            # Mark reminder as sent
            consultation.reminder_sent = True
            consultation.save(update_fields=['reminder_sent'])
            
            reminders_sent += 1
        
        logger.info(f"Sent {reminders_sent} consultation reminders")
        return {'reminders_sent': reminders_sent}
    
    except Exception as e:
        logger.error(f"Error sending consultation reminders: {str(e)}")
        return {'error': str(e)}


@shared_task
def update_consultation_statuses():
    """
    Update consultation statuses based on time
    Mark completed consultations
    """
    try:
        from experts.models import Consultation
        
        now = timezone.now()
        
        # Mark past consultations as completed
        past_consultations = Consultation.objects.filter(
            scheduled_time__lt=now - timedelta(hours=1),
            status='confirmed'
        )
        
        updated = past_consultations.update(status='completed')
        
        logger.info(f"Marked {updated} consultations as completed")
        return {'updated': updated}
    
    except Exception as e:
        logger.error(f"Error updating consultation statuses: {str(e)}")
        return {'error': str(e)}