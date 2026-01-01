from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'notification_type', 'title', 'is_read', 
        'read_at', 'created_at'
    )
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'title', 'message')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'notification_type', 'title', 'message')
        }),
        ('Related Object', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Additional Data', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_project_updates', 'email_new_messages', 'push_project_updates', 'updated_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email Notifications', {
            'fields': (
                'email_project_updates', 'email_new_messages', 
                'email_applications', 'email_reviews', 'email_marketing'
            )
        }),
        ('Push Notifications', {
            'fields': (
                'push_project_updates', 'push_new_messages', 
                'push_applications', 'push_reviews'
            )
        }),
        ('In-App Notifications', {
            'fields': (
                'inapp_project_updates', 'inapp_new_messages', 
                'inapp_applications', 'inapp_reviews'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )