from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.accounts.models import User
from apps.contractors.models import ContractorProfile
from apps.projects.models import Project


class Review(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_reviews')
    contractor = models.ForeignKey(ContractorProfile, on_delete=models.CASCADE, related_name='received_reviews')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)
    
    # Overall rating
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Overall rating from 1 to 5 stars"
    )
    
    # Category-specific ratings
    quality_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True,
        help_text="Quality of work rating"
    )
    communication_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True,
        help_text="Communication rating"
    )
    timeliness_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True,
        help_text="Timeliness rating"
    )
    professionalism_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True,
        help_text="Professionalism rating"
    )
    
    # Review content
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    
    # Metadata
    is_verified = models.BooleanField(default=False)  # Verified if from completed project
    is_featured = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reviews'
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        unique_together = ['client', 'contractor', 'project']  # One review per project
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contractor', 'is_public']),
            models.Index(fields=['rating', 'created_at']),
        ]

    def __str__(self):
        return f"{self.client.full_name} -> {self.contractor.user.full_name} ({self.rating}★)"

    def save(self, *args, **kwargs):
        # Set verified status based on project completion
        if self.project and self.project.status == 'completed':
            self.is_verified = True
        
        super().save(*args, **kwargs)
        
        # Update contractor's average rating
        self.contractor.update_rating(self.rating)

    @property
    def average_category_rating(self):
        """Calculate average of category-specific ratings"""
        ratings = [
            self.quality_rating,
            self.communication_rating,
            self.timeliness_rating,
            self.professionalism_rating
        ]
        valid_ratings = [r for r in ratings if r is not None]
        
        if valid_ratings:
            return sum(valid_ratings) / len(valid_ratings)
        return None


class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='review_images/')
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review_images'
        verbose_name = 'Review Image'
        verbose_name_plural = 'Review Images'

    def __str__(self):
        return f"Image for review {self.review.id}"


class ReviewResponse(models.Model):
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name='response')
    contractor = models.ForeignKey(User, on_delete=models.CASCADE)  # Should be contractor user
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'review_responses'
        verbose_name = 'Review Response'
        verbose_name_plural = 'Review Responses'

    def __str__(self):
        return f"Response to review {self.review.id}"

    def save(self, *args, **kwargs):
        # Ensure only the contractor can respond to their review
        if self.contractor != self.review.contractor.user:
            raise ValueError("Only the contractor can respond to their review")
        super().save(*args, **kwargs)


class ReviewHelpful(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_helpful = models.BooleanField()  # True for helpful, False for not helpful
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review_helpful'
        unique_together = ['review', 'user']
        verbose_name = 'Review Helpful Vote'
        verbose_name_plural = 'Review Helpful Votes'

    def __str__(self):
        helpful_text = "helpful" if self.is_helpful else "not helpful"
        return f"{self.user.full_name} found review {self.review.id} {helpful_text}"