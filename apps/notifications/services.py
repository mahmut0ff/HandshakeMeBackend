from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification, NotificationPreference
from .tasks import send_notification_email, send_push_notification


class NotificationService:
    """Service class for handling notifications"""
    
    @staticmethod
    def create_notification(
        user, 
        notification_type, 
        title, 
        message, 
        related_object=None, 
        extra_data=None,
        send_email=True,
        send_push=True
    ):
        """Create a new notification"""
        # Get user's notification preferences
        preferences, created = NotificationPreference.objects.get_or_create(
            user=user,
            defaults={
                'email_project_updates': True,
                'email_new_messages': True,
                'email_applications': True,
                'email_reviews': True,
                'push_project_updates': True,
                'push_new_messages': True,
                'push_applications': True,
                'push_reviews': True,
            }
        )
        
        # Create the notification
        notification_data = {
            'user': user,
            'notification_type': notification_type,
            'title': title,
            'message': message,
            'extra_data': extra_data or {}
        }
        
        if related_object:
            notification_data['content_type'] = ContentType.objects.get_for_model(related_object)
            notification_data['object_id'] = related_object.pk
        
        notification = Notification.objects.create(**notification_data)
        
        # Send real-time notification via WebSocket
        NotificationService._send_realtime_notification(user, notification)
        
        # Send email notification if enabled
        if send_email and NotificationService._should_send_email(preferences, notification_type):
            NotificationService._send_email_notification(notification)
        
        # Send push notification if enabled
        if send_push and NotificationService._should_send_push(preferences, notification_type):
            NotificationService._send_push_notification(notification)
        
        return notification
    
    @staticmethod
    def _send_realtime_notification(user, notification):
        """Send real-time notification via WebSocket"""
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}",
                {
                    'type': 'notification_message',
                    'notification': {
                        'id': notification.id,
                        'type': notification.notification_type,
                        'title': notification.title,
                        'message': notification.message,
                        'created_at': notification.created_at.isoformat(),
                        'is_read': notification.is_read,
                    }
                }
            )
    
    @staticmethod
    def _should_send_email(preferences, notification_type):
        """Check if email notification should be sent"""
        email_mapping = {
            'project_application': preferences.email_applications,
            'application_accepted': preferences.email_applications,
            'application_rejected': preferences.email_applications,
            'project_completed': preferences.email_project_updates,
            'project_update': preferences.email_project_updates,
            'new_message': preferences.email_new_messages,
            'review_received': preferences.email_reviews,
            'payment_reminder': preferences.email_project_updates,
            'system': True,  # Always send system notifications
        }
        return email_mapping.get(notification_type, False)
    
    @staticmethod
    def _should_send_push(preferences, notification_type):
        """Check if push notification should be sent"""
        push_mapping = {
            'project_application': preferences.push_applications,
            'application_accepted': preferences.push_applications,
            'application_rejected': preferences.push_applications,
            'project_completed': preferences.push_project_updates,
            'project_update': preferences.push_project_updates,
            'new_message': preferences.push_new_messages,
            'review_received': preferences.push_reviews,
            'payment_reminder': preferences.push_project_updates,
            'system': True,  # Always send system notifications
        }
        return push_mapping.get(notification_type, False)
    
    @staticmethod
    def _send_email_notification(notification):
        """Send email notification asynchronously"""
        send_notification_email.delay(notification.id)
    
    @staticmethod
    def _send_push_notification(notification):
        """Send push notification asynchronously"""
        send_push_notification.delay(notification.id)
    
    @staticmethod
    def mark_notifications_as_read(user, notification_ids=None):
        """Mark notifications as read"""
        notifications = Notification.objects.filter(user=user, is_read=False)
        
        if notification_ids:
            notifications = notifications.filter(id__in=notification_ids)
        
        from django.utils import timezone
        updated_count = notifications.update(is_read=True, read_at=timezone.now())
        
        return updated_count
    
    @staticmethod
    def get_unread_count(user):
        """Get unread notifications count for user"""
        return Notification.objects.filter(user=user, is_read=False).count()
    
    @staticmethod
    def get_user_notifications(user, limit=50, notification_type=None, is_read=None):
        """Get user notifications with filters"""
        notifications = Notification.objects.filter(user=user)
        
        if notification_type:
            notifications = notifications.filter(notification_type=notification_type)
        
        if is_read is not None:
            notifications = notifications.filter(is_read=is_read)
        
        return notifications.order_by('-created_at')[:limit]
    
    @staticmethod
    def delete_old_notifications(days=30):
        """Delete old notifications (cleanup task)"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count = Notification.objects.filter(
            created_at__lt=cutoff_date,
            is_read=True
        ).delete()[0]
        
        return deleted_count
    
    @staticmethod
    def create_bulk_notifications(notifications_data):
        """Create multiple notifications efficiently"""
        notifications = []
        
        for data in notifications_data:
            notification_obj = Notification(
                user=data['user'],
                notification_type=data['notification_type'],
                title=data['title'],
                message=data['message'],
                extra_data=data.get('extra_data', {})
            )
            
            if data.get('related_object'):
                notification_obj.content_type = ContentType.objects.get_for_model(data['related_object'])
                notification_obj.object_id = data['related_object'].pk
            
            notifications.append(notification_obj)
        
        created_notifications = Notification.objects.bulk_create(notifications)
        
        # Send real-time notifications
        for notification in created_notifications:
            NotificationService._send_realtime_notification(notification.user, notification)
        
        return created_notifications