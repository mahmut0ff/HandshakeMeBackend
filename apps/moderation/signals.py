from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from apps.projects.models import Project
from apps.chat.models import Message
from apps.reviews.models import Review
from .services import ContentModerationService

User = get_user_model()


@receiver(post_save, sender=Project)
def moderate_project_content(sender, instance, created, **kwargs):
    """Automatically moderate project content when created or updated"""
    if created or 'title' in getattr(instance, '_dirty_fields', []):
        # Analyze project title and description
        content = f"{instance.title} {instance.description}"
        ContentModerationService.analyze_content(content, instance)


@receiver(post_save, sender=Message)
def moderate_message_content(sender, instance, created, **kwargs):
    """Automatically moderate chat messages"""
    if created and instance.content:
        ContentModerationService.analyze_content(instance.content, instance)


@receiver(post_save, sender=Review)
def moderate_review_content(sender, instance, created, **kwargs):
    """Automatically moderate review content"""
    if created:
        content = f"{instance.title} {instance.comment}"
        ContentModerationService.analyze_content(content, instance)


@receiver(post_save, sender=User)
def moderate_user_profile(sender, instance, created, **kwargs):
    """Moderate user profile information"""
    if hasattr(instance, 'profile') and instance.profile:
        profile = instance.profile
        content = f"{profile.bio} {profile.skills}"
        ContentModerationService.analyze_content(content, profile)