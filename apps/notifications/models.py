from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from apps.accounts.models import User


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('project_application', 'Project Application'),
        ('application_accepted', 'Application Accepted'),
        ('application_rejected', 'Application Rejected'),
        ('project_completed', 'Project Completed'),
        ('project_update', 'Project Update'),
        ('new_message', 'New Message'),
        ('review_received', 'Review Received'),
        ('payment_reminder', 'Payment Reminder'),
        ('system', 'System Notification'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Generic foreign key to link to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Additional data as JSON
    extra_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email notifications
    email_project_updates = models.BooleanField(default=True)
    email_new_messages = models.BooleanField(default=True)
    email_applications = models.BooleanField(default=True)
    email_reviews = models.BooleanField(default=True)
    email_marketing = models.BooleanField(default=False)
    
    # Push notifications
    push_project_updates = models.BooleanField(default=True)
    push_new_messages = models.BooleanField(default=True)
    push_applications = models.BooleanField(default=True)
    push_reviews = models.BooleanField(default=True)
    
    # In-app notifications
    inapp_project_updates = models.BooleanField(default=True)
    inapp_new_messages = models.BooleanField(default=True)
    inapp_applications = models.BooleanField(default=True)
    inapp_reviews = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_preferences'
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        return f"{self.user.full_name} - Notification Preferences"