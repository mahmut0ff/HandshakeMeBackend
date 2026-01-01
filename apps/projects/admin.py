from django.contrib import admin
from .models import Project, ProjectImage, ProjectApplication, ProjectMilestone, ProjectUpdate, ProjectDocument


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


class ProjectMilestoneInline(admin.TabularInline):
    model = ProjectMilestone
    extra = 0
    ordering = ['order', 'due_date']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'client', 'contractor', 'category', 'status', 'priority',
        'budget_min', 'budget_max', 'progress_percentage', 'created_at'
    )
    list_filter = ('status', 'priority', 'category', 'created_at')
    search_fields = ('title', 'description', 'client__first_name', 'client__last_name', 'city', 'state')
    readonly_fields = ('views_count', 'applications_count', 'created_at', 'updated_at')
    inlines = [ProjectImageInline, ProjectMilestoneInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'client', 'contractor')
        }),
        ('Budget & Timeline', {
            'fields': ('budget_min', 'budget_max', 'start_date', 'end_date', 'deadline')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'postal_code', 'latitude', 'longitude')
        }),
        ('Status & Progress', {
            'fields': ('status', 'priority', 'progress_percentage')
        }),
        ('Metadata', {
            'fields': ('is_featured', 'views_count', 'applications_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ProjectApplication)
class ProjectApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'contractor', 'status', 'proposed_budget', 
        'proposed_timeline', 'applied_at'
    )
    list_filter = ('status', 'applied_at')
    search_fields = (
        'project__title', 'contractor__user__first_name', 
        'contractor__user__last_name', 'contractor__business_name'
    )
    readonly_fields = ('applied_at', 'updated_at')


@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'title', 'due_date', 'completion_date', 
        'status', 'payment_percentage', 'order'
    )
    list_filter = ('status', 'due_date', 'completion_date')
    search_fields = ('project__title', 'title', 'description')
    ordering = ['project', 'order', 'due_date']


@admin.register(ProjectUpdate)
class ProjectUpdateAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'author', 'title', 'progress_percentage', 
        'is_milestone_update', 'created_at'
    )
    list_filter = ('is_milestone_update', 'created_at')
    search_fields = ('project__title', 'title', 'content', 'author__first_name', 'author__last_name')
    readonly_fields = ('created_at',)


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'title', 'document_type', 'uploaded_by', 
        'is_private', 'created_at'
    )
    list_filter = ('document_type', 'is_private', 'created_at')
    search_fields = ('project__title', 'title', 'description', 'uploaded_by__first_name', 'uploaded_by__last_name')
    readonly_fields = ('created_at',)