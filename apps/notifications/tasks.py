from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Notification


@shared_task
def send_notification_email(notification_id):
    """Send email notification"""
    try:
        notification = Notification.objects.select_related('user').get(id=notification_id)
        
        # Prepare email context
        context = {
            'user': notification.user,
            'notification': notification,
            'site_name': 'Contractor Connect',
            'site_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000'),
        }
        
        # Render email templates
        subject = f"[Contractor Connect] {notification.title}"
        html_message = render_to_string('notifications/email_notification.html', context)
        plain_message = render_to_string('notifications/email_notification.txt', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Email sent successfully to {notification.user.email}"
        
    except Notification.DoesNotExist:
        return f"Notification {notification_id} not found"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


@shared_task
def send_push_notification(notification_id):
    """Send push notification (placeholder for actual push service integration)"""
    try:
        notification = Notification.objects.select_related('user').get(id=notification_id)
        
        # This is where you would integrate with a push notification service
        # like Firebase Cloud Messaging, Apple Push Notification Service, etc.
        
        # For now, we'll just log the notification
        print(f"Push notification sent to {notification.user.email}: {notification.title}")
        
        return f"Push notification sent to {notification.user.email}"
        
    except Notification.DoesNotExist:
        return f"Notification {notification_id} not found"
    except Exception as e:
        return f"Failed to send push notification: {str(e)}"


@shared_task
def cleanup_old_notifications():
    """Clean up old read notifications"""
    from .services import NotificationService
    
    deleted_count = NotificationService.delete_old_notifications(days=30)
    return f"Deleted {deleted_count} old notifications"


@shared_task
def send_daily_digest_emails():
    """Send daily digest emails to users with unread notifications"""
    from django.utils import timezone
    from datetime import timedelta
    from apps.accounts.models import User
    
    # Get users with unread notifications from the last 24 hours
    yesterday = timezone.now() - timedelta(days=1)
    
    users_with_notifications = User.objects.filter(
        notifications__is_read=False,
        notifications__created_at__gte=yesterday,
        notification_preferences__email_project_updates=True
    ).distinct()
    
    sent_count = 0
    
    for user in users_with_notifications:
        unread_notifications = user.notifications.filter(
            is_read=False,
            created_at__gte=yesterday
        ).order_by('-created_at')[:10]  # Limit to 10 most recent
        
        if unread_notifications.exists():
            context = {
                'user': user,
                'notifications': unread_notifications,
                'total_unread': user.notifications.filter(is_read=False).count(),
                'site_name': 'Contractor Connect',
                'site_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000'),
            }
            
            subject = f"[Contractor Connect] Daily Digest - {unread_notifications.count()} unread notifications"
            html_message = render_to_string('notifications/daily_digest.html', context)
            plain_message = render_to_string('notifications/daily_digest.txt', context)
            
            try:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=True,
                )
                sent_count += 1
            except Exception as e:
                print(f"Failed to send digest email to {user.email}: {str(e)}")
    
    return f"Sent daily digest emails to {sent_count} users"