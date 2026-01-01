from django.contrib import admin
from .models import Advertisement, AdCategory, AdCategoryAssignment


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ['title', 'position', 'target_audience', 'is_active', 'priority', 'impressions', 'clicks', 'click_through_rate']
    list_filter = ['ad_type', 'position', 'target_audience', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['impressions', 'clicks', 'click_through_rate', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'image', 'link_url', 'button_text')
        }),
        ('Targeting', {
            'fields': ('ad_type', 'position', 'target_audience')
        }),
        ('Styling', {
            'fields': ('background_color', 'text_color')
        }),
        ('Scheduling', {
            'fields': ('start_date', 'end_date', 'priority', 'is_active')
        }),
        ('Analytics', {
            'fields': ('impressions', 'clicks'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new ad
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AdCategory)
class AdCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']


@admin.register(AdCategoryAssignment)
class AdCategoryAssignmentAdmin(admin.ModelAdmin):
    list_display = ['advertisement', 'category', 'created_at']
    list_filter = ['category', 'created_at']