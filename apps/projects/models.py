from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.accounts.models import User
from apps.contractors.models import Category, ContractorProfile


class Project(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_projects')
    contractor = models.ForeignKey(
        ContractorProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='contractor_projects'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    budget_min = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Location details
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    # Timeline
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    
    # Progress tracking
    progress_percentage = models.PositiveIntegerField(
        default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Metadata
    is_featured = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    applications_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.client.full_name}"

    @property
    def average_budget(self):
        return (self.budget_min + self.budget_max) / 2

    @property
    def is_active(self):
        return self.status in ['published', 'in_progress']

    def increment_views(self):
        """Increment project views count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='projects/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_images'
        verbose_name = 'Project Image'
        verbose_name_plural = 'Project Images'

    def __str__(self):
        return f"{self.project.title} - Image"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per project
        if self.is_primary:
            ProjectImage.objects.filter(project=self.project, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class ProjectApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='applications')
    contractor = models.ForeignKey(ContractorProfile, on_delete=models.CASCADE, related_name='applications')
    cover_letter = models.TextField()
    proposed_budget = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    proposed_timeline = models.PositiveIntegerField(help_text="Proposed timeline in days")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_applications'
        verbose_name = 'Project Application'
        verbose_name_plural = 'Project Applications'
        unique_together = ['project', 'contractor']
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.contractor.user.full_name} - {self.project.title}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update project applications count
        if is_new:
            self.project.applications_count += 1
            self.project.save(update_fields=['applications_count'])


class ProjectMilestone(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    completion_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of total project payment for this milestone"
    )
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_milestones'
        verbose_name = 'Project Milestone'
        verbose_name_plural = 'Project Milestones'
        ordering = ['order', 'due_date']

    def __str__(self):
        return f"{self.project.title} - {self.title}"

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.due_date < timezone.now().date() and self.status != 'completed'


class ProjectUpdate(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='updates')
    author = models.ForeignKey(User, on_delete=models.CASCADE)  # Can be client or contractor
    title = models.CharField(max_length=200)
    content = models.TextField()
    progress_percentage = models.PositiveIntegerField(
        blank=True, 
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    is_milestone_update = models.BooleanField(default=False)
    milestone = models.ForeignKey(
        ProjectMilestone, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='updates'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_updates'
        verbose_name = 'Project Update'
        verbose_name_plural = 'Project Updates'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.title} - {self.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update project progress if specified
        if self.progress_percentage is not None:
            self.project.progress_percentage = self.progress_percentage
            self.project.save(update_fields=['progress_percentage'])


class ProjectDocument(models.Model):
    DOCUMENT_TYPES = [
        ('contract', 'Contract'),
        ('blueprint', 'Blueprint'),
        ('permit', 'Permit'),
        ('invoice', 'Invoice'),
        ('receipt', 'Receipt'),
        ('other', 'Other'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other')
    file = models.FileField(upload_to='project_documents/')
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_private = models.BooleanField(default=False)  # Only visible to client and assigned contractor
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_documents'
        verbose_name = 'Project Document'
        verbose_name_plural = 'Project Documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.title} - {self.title}"