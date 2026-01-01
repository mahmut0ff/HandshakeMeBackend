import re
import time
from typing import Dict, List, Any, Optional
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from decimal import Decimal

from .models import (
    ModerationRule, ContentFilter, ModerationAction, 
    ModerationQueue, UserWarning, ContentReport
)


class ContentModerationService:
    """Service for content moderation and filtering"""
    
    # Basic profanity word list (in production, use a comprehensive database)
    PROFANITY_WORDS = [
        'spam', 'scam', 'fake', 'fraud', 'cheat', 'steal',
        # Add more words as needed
    ]
    
    # Spam indicators
    SPAM_PATTERNS = [
        r'(?i)\b(buy now|click here|limited time|act fast)\b',
        r'(?i)\b(100% guaranteed|risk free|no obligation)\b',
        r'(?i)\b(make money fast|work from home|easy money)\b',
        r'(?i)\b(free trial|special offer|exclusive deal)\b',
    ]
    
    @classmethod
    def analyze_content(cls, content: str, content_object: Any) -> ContentFilter:
        """Analyze content and create filter record"""
        start_time = time.time()
        
        # Get or create content filter
        content_type = ContentType.objects.get_for_model(content_object)
        content_filter, created = ContentFilter.objects.get_or_create(
            content_type=content_type,
            object_id=content_object.pk,
            defaults={
                'profanity_score': 0.0,
                'spam_score': 0.0,
                'toxicity_score': 0.0,
                'sentiment_score': 0.0,
            }
        )
        
        if not created and content_filter.processed_at:
            # Already processed, return existing
            return content_filter
        
        # Analyze content
        profanity_score = cls._calculate_profanity_score(content)
        spam_score = cls._calculate_spam_score(content)
        toxicity_score = cls._calculate_toxicity_score(content)
        sentiment_score = cls._calculate_sentiment_score(content)
        
        # Calculate overall risk level
        risk_level = cls._calculate_risk_level(
            profanity_score, spam_score, toxicity_score
        )
        
        # Update content filter
        content_filter.profanity_score = profanity_score
        content_filter.spam_score = spam_score
        content_filter.toxicity_score = toxicity_score
        content_filter.sentiment_score = sentiment_score
        content_filter.risk_level = risk_level
        content_filter.requires_review = risk_level in ['high', 'critical']
        content_filter.is_approved = risk_level in ['low', 'medium']
        content_filter.processing_time = time.time() - start_time
        content_filter.save()
        
        # Apply moderation rules
        cls._apply_moderation_rules(content, content_object, content_filter)
        
        # Add to moderation queue if needed
        if content_filter.requires_review:
            cls._add_to_moderation_queue(content_object, content_filter)
        
        return content_filter
    
    @classmethod
    def _calculate_profanity_score(cls, content: str) -> float:
        """Calculate profanity score (0.0 to 1.0)"""
        if not content:
            return 0.0
        
        words = content.lower().split()
        profane_count = sum(1 for word in words if word in cls.PROFANITY_WORDS)
        
        if len(words) == 0:
            return 0.0
        
        return min(profane_count / len(words) * 5, 1.0)  # Scale up for impact
    
    @classmethod
    def _calculate_spam_score(cls, content: str) -> float:
        """Calculate spam score (0.0 to 1.0)"""
        if not content:
            return 0.0
        
        spam_indicators = 0
        
        # Check for spam patterns
        for pattern in cls.SPAM_PATTERNS:
            if re.search(pattern, content):
                spam_indicators += 1
        
        # Check for excessive capitalization
        if len(content) > 10:
            caps_ratio = sum(1 for c in content if c.isupper()) / len(content)
            if caps_ratio > 0.5:
                spam_indicators += 1
        
        # Check for excessive punctuation
        punct_ratio = sum(1 for c in content if c in '!?') / max(len(content), 1)
        if punct_ratio > 0.1:
            spam_indicators += 1
        
        # Check for repeated characters
        if re.search(r'(.)\1{3,}', content):
            spam_indicators += 1
        
        return min(spam_indicators / 5, 1.0)
    
    @classmethod
    def _calculate_toxicity_score(cls, content: str) -> float:
        """Calculate toxicity score (0.0 to 1.0)"""
        # In production, integrate with Google's Perspective API or similar
        # For now, use basic heuristics
        
        if not content:
            return 0.0
        
        toxic_indicators = [
            'hate', 'stupid', 'idiot', 'kill', 'die', 'threat',
            'violence', 'attack', 'hurt', 'destroy'
        ]
        
        words = content.lower().split()
        toxic_count = sum(1 for word in words if word in toxic_indicators)
        
        return min(toxic_count / max(len(words), 1) * 10, 1.0)
    
    @classmethod
    def _calculate_sentiment_score(cls, content: str) -> float:
        """Calculate sentiment score (-1.0 to 1.0)"""
        # Basic sentiment analysis
        positive_words = [
            'good', 'great', 'excellent', 'amazing', 'wonderful',
            'fantastic', 'awesome', 'perfect', 'love', 'like'
        ]
        
        negative_words = [
            'bad', 'terrible', 'awful', 'horrible', 'hate',
            'dislike', 'worst', 'poor', 'disappointing', 'sad'
        ]
        
        words = content.lower().split()
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        if len(words) == 0:
            return 0.0
        
        sentiment = (positive_count - negative_count) / len(words)
        return max(-1.0, min(1.0, sentiment * 5))  # Scale and clamp
    
    @classmethod
    def _calculate_risk_level(cls, profanity: float, spam: float, toxicity: float) -> str:
        """Calculate overall risk level"""
        max_score = max(profanity, spam, toxicity)
        
        if max_score >= 0.8:
            return 'critical'
        elif max_score >= 0.6:
            return 'high'
        elif max_score >= 0.3:
            return 'medium'
        else:
            return 'low'
    
    @classmethod
    def _apply_moderation_rules(cls, content: str, content_object: Any, 
                              content_filter: ContentFilter):
        """Apply active moderation rules"""
        rules = ModerationRule.objects.filter(is_active=True)
        
        for rule in rules:
            if cls._rule_matches(rule, content, content_filter):
                cls._execute_rule_action(rule, content_object, content_filter)
    
    @classmethod
    def _rule_matches(cls, rule: ModerationRule, content: str, 
                     content_filter: ContentFilter) -> bool:
        """Check if content matches a moderation rule"""
        if rule.rule_type == 'profanity':
            return content_filter.profanity_score >= rule.confidence_threshold
        elif rule.rule_type == 'spam':
            return content_filter.spam_score >= rule.confidence_threshold
        elif rule.rule_type == 'inappropriate':
            return content_filter.toxicity_score >= rule.confidence_threshold
        elif rule.rule_type == 'custom':
            # Check keywords and patterns
            for keyword in rule.keywords:
                if keyword.lower() in content.lower():
                    return True
            
            for pattern in rule.patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
        
        return False
    
    @classmethod
    def _execute_rule_action(cls, rule: ModerationRule, content_object: Any,
                           content_filter: ContentFilter):
        """Execute the action defined by a moderation rule"""
        content_type = ContentType.objects.get_for_model(content_object)
        
        # Create moderation action record
        action_type = {
            'flag': 'flagged',
            'auto_reject': 'rejected',
            'auto_approve': 'approved',
            'quarantine': 'quarantined',
        }.get(rule.action, 'flagged')
        
        ModerationAction.objects.create(
            content_type=content_type,
            object_id=content_object.pk,
            action=action_type,
            reason=f"Triggered rule: {rule.name}",
            moderator_id=1,  # System user
            is_automated=True,
            rule=rule,
            metadata={'rule_id': str(rule.id), 'confidence': content_filter.ai_confidence}
        )
        
        # Apply the action
        if rule.action == 'auto_reject':
            content_filter.is_approved = False
            content_filter.requires_review = True
        elif rule.action == 'quarantine':
            content_filter.is_approved = False
            content_filter.requires_review = True
        elif rule.action == 'flag':
            content_filter.requires_review = True
        
        content_filter.save()
    
    @classmethod
    def _add_to_moderation_queue(cls, content_object: Any, 
                               content_filter: ContentFilter):
        """Add content to moderation queue"""
        content_type = ContentType.objects.get_for_model(content_object)
        
        # Determine priority based on risk level
        priority_map = {
            'critical': 'urgent',
            'high': 'high',
            'medium': 'normal',
            'low': 'low'
        }
        
        ModerationQueue.objects.get_or_create(
            content_type=content_type,
            object_id=content_object.pk,
            defaults={
                'priority': priority_map.get(content_filter.risk_level, 'normal'),
                'content_filter': content_filter,
            }
        )


class ReportingService:
    """Service for handling user reports"""
    
    @classmethod
    def create_report(cls, reporter, content_object, report_type: str, 
                     description: str, evidence: List[str] = None) -> ContentReport:
        """Create a new content report"""
        content_type = ContentType.objects.get_for_model(content_object)
        
        report = ContentReport.objects.create(
            reporter=reporter,
            content_type=content_type,
            object_id=content_object.pk,
            report_type=report_type,
            description=description,
            evidence=evidence or []
        )
        
        # Add to moderation queue with high priority
        queue_item, created = ModerationQueue.objects.get_or_create(
            content_type=content_type,
            object_id=content_object.pk,
            defaults={'priority': 'high'}
        )
        
        if created:
            queue_item.reports.add(report)
        
        return report
    
    @classmethod
    def resolve_report(cls, report: ContentReport, moderator, 
                      resolution_notes: str, action: str = None):
        """Resolve a content report"""
        report.status = 'resolved'
        report.reviewed_by = moderator
        report.resolution_notes = resolution_notes
        report.resolved_at = timezone.now()
        report.save()
        
        if action:
            # Create moderation action
            ModerationAction.objects.create(
                content_type=report.content_type,
                object_id=report.object_id,
                action=action,
                reason=f"Report resolution: {resolution_notes}",
                moderator=moderator,
                report=report
            )


class ModerationQueueService:
    """Service for managing moderation queue"""
    
    @classmethod
    def assign_to_moderator(cls, queue_item: ModerationQueue, moderator):
        """Assign queue item to a moderator"""
        queue_item.assigned_to = moderator
        queue_item.assigned_at = timezone.now()
        queue_item.status = 'in_progress'
        queue_item.save()
    
    @classmethod
    def complete_moderation(cls, queue_item: ModerationQueue, 
                          action: str, reason: str, moderator):
        """Complete moderation for a queue item"""
        # Create moderation action
        ModerationAction.objects.create(
            content_type=queue_item.content_type,
            object_id=queue_item.object_id,
            action=action,
            reason=reason,
            moderator=moderator
        )
        
        # Update queue item
        queue_item.status = 'completed'
        queue_item.completed_at = timezone.now()
        queue_item.save()
        
        # Update content filter if exists
        if queue_item.content_filter:
            queue_item.content_filter.is_approved = action in ['approved']
            queue_item.content_filter.requires_review = False
            queue_item.content_filter.save()
    
    @classmethod
    def get_next_item_for_moderator(cls, moderator) -> Optional[ModerationQueue]:
        """Get next item in queue for a moderator"""
        return ModerationQueue.objects.filter(
            status='pending'
        ).order_by('-priority', 'created_at').first()


class UserModerationService:
    """Service for user-level moderation actions"""
    
    @classmethod
    def issue_warning(cls, user, warning_type: str, severity: str,
                     title: str, message: str, issued_by, 
                     related_action: ModerationAction = None) -> UserWarning:
        """Issue a warning to a user"""
        warning = UserWarning.objects.create(
            user=user,
            warning_type=warning_type,
            severity=severity,
            title=title,
            message=message,
            issued_by=issued_by,
            related_action=related_action
        )
        
        # Check if user should be suspended based on warning count
        cls._check_user_suspension(user)
        
        return warning
    
    @classmethod
    def _check_user_suspension(cls, user):
        """Check if user should be suspended based on warnings"""
        recent_warnings = UserWarning.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        )
        
        critical_warnings = recent_warnings.filter(severity='critical').count()
        high_warnings = recent_warnings.filter(severity='high').count()
        
        # Suspension logic
        if critical_warnings >= 2 or high_warnings >= 5:
            cls._suspend_user(user, days=7, reason="Multiple policy violations")
        elif critical_warnings >= 3 or high_warnings >= 10:
            cls._suspend_user(user, days=30, reason="Repeated policy violations")
    
    @classmethod
    def _suspend_user(cls, user, days: int, reason: str):
        """Suspend a user account"""
        user.is_active = False
        user.save()
        
        # Create moderation action
        from django.contrib.contenttypes.models import ContentType
        user_content_type = ContentType.objects.get_for_model(user)
        
        ModerationAction.objects.create(
            content_type=user_content_type,
            object_id=user.pk,
            action='user_suspended',
            reason=reason,
            moderator_id=1,  # System user
            is_automated=True,
            metadata={'suspension_days': days}
        )