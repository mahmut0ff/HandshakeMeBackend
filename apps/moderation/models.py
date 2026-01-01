from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid

User = get_user_model()


class ModerationRule(models.Model):
    """Content moderation rules"""
    RULE_TYPES = [
        ('profanity', 'Profanity Filter'),
        ('spam', 'Spam Detection'),
        ('inappropriate', 'Inappropriate Content'),
        ('copyright', 'Copyright Violation'),
        ('personal_info', 'Personal Information'),
        ('custom', 'Custom Rule'),
    ]
    
    ACTION_TYPES = [
        ('flag', 'Flag for Review'),
        ('auto_reject', 'Auto Reject'),
        ('auto_approve', 'Auto Approve'),
        ('quarantine', 'Quarantine'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    
    # Rule configuration
    keywords = models.JSONField(default=list, blank=True)  # List of keywords to match
    patterns = models.JSONField(default=list, blank=True)  # Regex patterns
    confidence_threshold = models.FloatField(default=0.8)  # AI confidence threshold
    
    action = models.CharField(max_length=20, choices=ACTION_TYPES, default='flag')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'moderation_rules'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"


class ContentReport(models.Model):
    """User reports for content"""
    REPORT_TYPES = [
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('inappropriate', 'Inappropriate Content'),
        ('copyright', 'Copyright Violation'),
        ('fake_profile', 'Fake Profile'),
        ('scam', 'Scam/Fraud'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Reporter information
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_reports')
    
    # Reported content (generic relation)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Report details
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField()
    evidence = models.JSONField(default=list, blank=True)  # Screenshots, links, etc.
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Resolution
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_reports')
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'content_reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"Report {self.id} - {self.get_report_type_display()}"


class ModerationAction(models.Model):
    """Actions taken on content"""
    ACTION_TYPES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged'),
        ('quarantined', 'Quarantined'),
        ('deleted', 'Deleted'),
        ('edited', 'Edited'),
        ('warning_issued', 'Warning Issued'),
        ('user_suspended', 'User Suspended'),
        ('user_banned', 'User Banned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Content being moderated
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Action details
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    reason = models.TextField()
    
    # Moderator information
    moderator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moderation_actions')
    is_automated = models.BooleanField(default=False)
    
    # Related rule or report
    rule = models.ForeignKey(ModerationRule, on_delete=models.SET_NULL, null=True, blank=True)
    report = models.ForeignKey(ContentReport, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'moderation_actions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['moderator', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.content_type.model}"


class UserWarning(models.Model):
    """Warnings issued to users"""
    WARNING_TYPES = [
        ('content_violation', 'Content Policy Violation'),
        ('spam', 'Spam Behavior'),
        ('harassment', 'Harassment'),
        ('inappropriate_conduct', 'Inappropriate Conduct'),
        ('terms_violation', 'Terms of Service Violation'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='warnings')
    warning_type = models.CharField(max_length=30, choices=WARNING_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related content or action
    related_action = models.ForeignKey(ModerationAction, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Warning status
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Issued by
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='warnings_issued')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_warnings'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Warning for {self.user.email} - {self.title}"


class ContentFilter(models.Model):
    """Content filtering and scoring"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Content being filtered
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Filtering results
    profanity_score = models.FloatField(default=0.0)
    spam_score = models.FloatField(default=0.0)
    toxicity_score = models.FloatField(default=0.0)
    sentiment_score = models.FloatField(default=0.0)  # -1 to 1 (negative to positive)
    
    # AI analysis results
    ai_confidence = models.FloatField(default=0.0)
    ai_tags = models.JSONField(default=list, blank=True)
    
    # Overall assessment
    risk_level = models.CharField(max_length=10, choices=[
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ], default='low')
    
    requires_review = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    
    # Processing metadata
    processed_at = models.DateTimeField(auto_now_add=True)
    processing_time = models.FloatField(default=0.0)  # seconds
    
    class Meta:
        db_table = 'content_filters'
        ordering = ['-processed_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['risk_level', 'requires_review']),
        ]
    
    def __str__(self):
        return f"Filter for {self.content_type.model} - {self.risk_level} risk"


class ModerationQueue(models.Model):
    """Queue for content awaiting moderation"""
    PRIORITY_LEVELS = [
        ('low', 'Low Priority'),
        ('normal', 'Normal Priority'),
        ('high', 'High Priority'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('escalated', 'Escalated'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Content to be moderated
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Queue details
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='normal')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_moderations')
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    # Related objects
    content_filter = models.ForeignKey(ContentFilter, on_delete=models.SET_NULL, null=True, blank=True)
    reports = models.ManyToManyField(ContentReport, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'moderation_queue'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self):
        return f"Queue Item {self.id} - {self.get_priority_display()}"