from django.db.models import Q, Avg, Count, Case, When, Value, DecimalField
from django.utils import timezone
from django.core.cache import cache
from .models import Project, ProjectApplication, ProjectMilestone
from apps.contractors.models import ContractorProfile
from apps.notifications.services import NotificationService


class ProjectService:
    """Service class for project-related business logic"""
    
    @staticmethod
    def search_projects(
        query=None,
        category=None,
        status=None,
        min_budget=None,
        max_budget=None,
        priority=None,
        location=None,
        client_id=None,
        contractor_id=None,
        limit=20,
        offset=0
    ):
        """Advanced project search with multiple filters"""
        projects = Project.objects.select_related('client', 'contractor__user', 'category').prefetch_related('images')
        
        # Text search
        if query:
            projects = projects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(client__first_name__icontains=query) |
                Q(client__last_name__icontains=query)
            )
        
        # Category filter
        if category:
            projects = projects.filter(category_id=category)
        
        # Status filter
        if status:
            if isinstance(status, list):
                projects = projects.filter(status__in=status)
            else:
                projects = projects.filter(status=status)
        
        # Budget filters
        if min_budget:
            projects = projects.filter(budget_max__gte=min_budget)
        if max_budget:
            projects = projects.filter(budget_min__lte=max_budget)
        
        # Priority filter
        if priority:
            projects = projects.filter(priority=priority)
        
        # Location filter
        if location:
            projects = projects.filter(
                Q(city__icontains=location) |
                Q(state__icontains=location) |
                Q(address__icontains=location)
            )
        
        # Client filter
        if client_id:
            projects = projects.filter(client_id=client_id)
        
        # Contractor filter
        if contractor_id:
            projects = projects.filter(contractor_id=contractor_id)
        
        # Order by priority and creation date
        priority_order = Case(
            When(priority='urgent', then=Value(4)),
            When(priority='high', then=Value(3)),
            When(priority='medium', then=Value(2)),
            When(priority='low', then=Value(1)),
            default=Value(0),
            output_field=DecimalField()
        )
        
        projects = projects.annotate(priority_score=priority_order).order_by(
            '-priority_score', '-created_at'
        )
        
        return projects[offset:offset + limit]
    
    @staticmethod
    def get_project_stats():
        """Get cached project statistics"""
        cache_key = "project_stats"
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = {
                'total_projects': Project.objects.count(),
                'active_projects': Project.objects.filter(status__in=['published', 'in_progress']).count(),
                'completed_projects': Project.objects.filter(status='completed').count(),
                'avg_budget': Project.objects.aggregate(
                    avg_budget=Avg('budget_min') + Avg('budget_max')
                )['avg_budget'] or 0,
                'total_applications': ProjectApplication.objects.count(),
                'avg_applications_per_project': Project.objects.aggregate(
                    avg_apps=Avg('applications_count')
                )['avg_apps'] or 0,
            }
            cache.set(cache_key, stats, timeout=3600)  # Cache for 1 hour
        
        return stats
    
    @staticmethod
    def apply_to_project(contractor_profile, project, application_data):
        """Handle contractor application to project"""
        # Check if contractor already applied
        existing_application = ProjectApplication.objects.filter(
            project=project,
            contractor=contractor_profile
        ).first()
        
        if existing_application:
            raise ValueError("You have already applied to this project")
        
        # Check if project is still accepting applications
        if project.status != 'published':
            raise ValueError("This project is no longer accepting applications")
        
        # Create application
        application = ProjectApplication.objects.create(
            project=project,
            contractor=contractor_profile,
            **application_data
        )
        
        # Send notification to client
        NotificationService.create_notification(
            user=project.client,
            notification_type='project_application',
            title='New Project Application',
            message=f'{contractor_profile.user.full_name} applied to your project "{project.title}"',
            related_object=application
        )
        
        return application
    
    @staticmethod
    def accept_application(project, application_id, client_user):
        """Accept a project application"""
        if project.client != client_user:
            raise ValueError("Only the project owner can accept applications")
        
        application = ProjectApplication.objects.get(id=application_id, project=project)
        
        if application.status != 'pending':
            raise ValueError("This application has already been processed")
        
        # Accept the application
        application.status = 'accepted'
        application.save()
        
        # Assign contractor to project
        project.contractor = application.contractor
        project.status = 'in_progress'
        project.save()
        
        # Reject all other pending applications
        ProjectApplication.objects.filter(
            project=project,
            status='pending'
        ).exclude(id=application_id).update(status='rejected')
        
        # Send notifications
        NotificationService.create_notification(
            user=application.contractor.user,
            notification_type='application_accepted',
            title='Application Accepted',
            message=f'Your application for "{project.title}" has been accepted!',
            related_object=project
        )
        
        return application
    
    @staticmethod
    def update_project_progress(project, progress_percentage, update_data=None):
        """Update project progress and create update entry"""
        project.progress_percentage = progress_percentage
        project.save(update_fields=['progress_percentage'])
        
        if update_data:
            from .models import ProjectUpdate
            ProjectUpdate.objects.create(
                project=project,
                progress_percentage=progress_percentage,
                **update_data
            )
        
        # Check if project should be marked as completed
        if progress_percentage >= 100 and project.status == 'in_progress':
            project.status = 'completed'
            project.save(update_fields=['status'])
            
            # Send completion notification
            NotificationService.create_notification(
                user=project.client,
                notification_type='project_completed',
                title='Project Completed',
                message=f'Your project "{project.title}" has been completed!',
                related_object=project
            )
    
    @staticmethod
    def get_overdue_milestones():
        """Get all overdue milestones"""
        today = timezone.now().date()
        return ProjectMilestone.objects.filter(
            due_date__lt=today,
            status__in=['pending', 'in_progress']
        ).select_related('project')
    
    @staticmethod
    def get_recommended_projects_for_contractor(contractor_profile, limit=10):
        """Get recommended projects for a contractor based on their profile"""
        # Get projects in contractor's categories
        projects = Project.objects.filter(
            status='published',
            category__in=contractor_profile.categories.all()
        ).select_related('client', 'category').prefetch_related('images')
        
        # Filter by budget range (projects within contractor's rate range)
        contractor_daily_rate = contractor_profile.average_hourly_rate * 8  # 8 hours per day
        projects = projects.filter(
            budget_min__lte=contractor_daily_rate * 30,  # Assume max 30 days
            budget_max__gte=contractor_daily_rate * 5    # Assume min 5 days
        )
        
        # Exclude projects contractor already applied to
        applied_project_ids = ProjectApplication.objects.filter(
            contractor=contractor_profile
        ).values_list('project_id', flat=True)
        
        projects = projects.exclude(id__in=applied_project_ids)
        
        # Order by priority and creation date
        priority_order = Case(
            When(priority='urgent', then=Value(4)),
            When(priority='high', then=Value(3)),
            When(priority='medium', then=Value(2)),
            When(priority='low', then=Value(1)),
            default=Value(0),
            output_field=DecimalField()
        )
        
        projects = projects.annotate(priority_score=priority_order).order_by(
            '-priority_score', '-created_at'
        )[:limit]
        
        return projects
    
    @staticmethod
    def increment_project_views(project):
        """Increment project view count"""
        project.increment_views()
        
        # Clear cache to refresh stats
        cache.delete("project_stats")