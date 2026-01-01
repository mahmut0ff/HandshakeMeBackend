from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.accounts.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True)  # For emoji or icon class
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='skills')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'skills'
        verbose_name = 'Skill'
        verbose_name_plural = 'Skills'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class ContractorProfile(models.Model):
    EXPERIENCE_CHOICES = [
        ('beginner', 'Beginner (0-2 years)'),
        ('intermediate', 'Intermediate (2-5 years)'),
        ('experienced', 'Experienced (5-10 years)'),
        ('expert', 'Expert (10+ years)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='contractor_profile')
    business_name = models.CharField(max_length=200, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    insurance_verified = models.BooleanField(default=False)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default='beginner')
    hourly_rate_min = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)])
    hourly_rate_max = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)])
    availability_status = models.BooleanField(default=True)
    response_time_hours = models.PositiveIntegerField(default=24)  # Average response time in hours
    completed_projects = models.PositiveIntegerField(default=0)
    rating_average = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    rating_count = models.PositiveIntegerField(default=0)
    categories = models.ManyToManyField(Category, related_name='contractors')
    skills = models.ManyToManyField(Skill, related_name='contractors')
    service_radius = models.PositiveIntegerField(default=25)  # Service radius in miles
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contractor_profiles'
        verbose_name = 'Contractor Profile'
        verbose_name_plural = 'Contractor Profiles'

    def __str__(self):
        return f"{self.user.full_name} - {self.business_name or 'Contractor'}"

    @property
    def average_hourly_rate(self):
        return (self.hourly_rate_min + self.hourly_rate_max) / 2

    def update_rating(self, new_rating):
        """Update contractor's average rating"""
        total_rating = (self.rating_average * self.rating_count) + new_rating
        self.rating_count += 1
        self.rating_average = total_rating / self.rating_count
        self.save(update_fields=['rating_average', 'rating_count'])


class Portfolio(models.Model):
    contractor = models.ForeignKey(ContractorProfile, on_delete=models.CASCADE, related_name='portfolio_items')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    project_date = models.DateField()
    project_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    client_name = models.CharField(max_length=100, blank=True)  # Optional, for testimonials
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'portfolio_items'
        verbose_name = 'Portfolio Item'
        verbose_name_plural = 'Portfolio Items'
        ordering = ['-project_date']

    def __str__(self):
        return f"{self.contractor.user.full_name} - {self.title}"


class PortfolioImage(models.Model):
    portfolio_item = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='portfolio/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'portfolio_images'
        verbose_name = 'Portfolio Image'
        verbose_name_plural = 'Portfolio Images'

    def __str__(self):
        return f"{self.portfolio_item.title} - Image"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per portfolio item
        if self.is_primary:
            PortfolioImage.objects.filter(
                portfolio_item=self.portfolio_item, 
                is_primary=True
            ).update(is_primary=False)
        super().save(*args, **kwargs)


class Certification(models.Model):
    contractor = models.ForeignKey(ContractorProfile, on_delete=models.CASCADE, related_name='certifications')
    name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    certificate_image = models.ImageField(upload_to='certifications/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'certifications'
        verbose_name = 'Certification'
        verbose_name_plural = 'Certifications'
        ordering = ['-issue_date']

    def __str__(self):
        return f"{self.contractor.user.full_name} - {self.name}"

    @property
    def is_expired(self):
        if self.expiry_date:
            from django.utils import timezone
            return timezone.now().date() > self.expiry_date
        return False