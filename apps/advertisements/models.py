from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.accounts.models import User


class Advertisement(models.Model):
    AD_TYPE_CHOICES = [
        ('banner', 'Banner'),
        ('slider', 'Slider'),
        ('popup', 'Popup'),
        ('sponsored', 'Sponsored Content'),
    ]
    
    POSITION_CHOICES = [
        ('home_slider', 'Home Page Slider'),
        ('home_banner', 'Home Page Banner'),
        ('search_results', 'Search Results'),
        ('project_details', 'Project Details'),
        ('profile_page', 'Profile Page'),
    ]
    
    TARGET_AUDIENCE_CHOICES = [
        ('all', 'All Users'),
        ('contractors', 'Contractors Only'),
        ('clients', 'Clients Only'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='advertisements/')
    link_url = models.URLField(blank=True, null=True)
    button_text = models.CharField(max_length=50, default='Learn More')
    
    ad_type = models.CharField(max_length=20, choices=AD_TYPE_CHOICES, default='banner')
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='home_slider')
    target_audience = models.CharField(max_length=20, choices=TARGET_AUDIENCE_CHOICES, default='all')
    
    # Styling
    background_color = models.CharField(max_length=7, default='#f97316')  # Hex color
    text_color = models.CharField(max_length=7, default='#ffffff')
    
    # Scheduling
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Priority and status
    priority = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Higher number = higher priority"
    )
    is_active = models.BooleanField(default=True)
    
    # Analytics
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_ads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'advertisements'
        verbose_name = 'Advertisement'
        verbose_name_plural = 'Advertisements'
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.position})"

    @property
    def click_through_rate(self):
        """Calculate CTR as percentage"""
        if self.impressions == 0:
            return 0
        return (self.clicks / self.impressions) * 100

    @property
    def is_currently_active(self):
        """Check if ad is active and within date range"""
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and 
            self.start_date <= now <= self.end_date
        )

    def increment_impressions(self):
        """Increment impression count"""
        self.impressions += 1
        self.save(update_fields=['impressions'])

    def increment_clicks(self):
        """Increment click count"""
        self.clicks += 1
        self.save(update_fields=['clicks'])


class AdCategory(models.Model):
    """Categories for targeted advertising"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_categories'
        verbose_name = 'Ad Category'
        verbose_name_plural = 'Ad Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class AdCategoryAssignment(models.Model):
    """Many-to-many relationship between ads and categories"""
    advertisement = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name='category_assignments')
    category = models.ForeignKey(AdCategory, on_delete=models.CASCADE, related_name='ad_assignments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_category_assignments'
        unique_together = ['advertisement', 'category']

    def __str__(self):
        return f"{self.advertisement.title} - {self.category.name}"