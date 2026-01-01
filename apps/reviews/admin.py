from django.contrib import admin
from .models import Review, ReviewImage, ReviewResponse, ReviewHelpful


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 1


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'client', 'contractor', 'project', 'rating', 'is_verified', 
        'is_featured', 'is_public', 'created_at'
    )
    list_filter = ('rating', 'is_verified', 'is_featured', 'is_public', 'created_at')
    search_fields = (
        'client__first_name', 'client__last_name', 'contractor__user__first_name',
        'contractor__user__last_name', 'contractor__business_name', 'title', 'comment'
    )
    readonly_fields = ('average_category_rating', 'created_at', 'updated_at')
    inlines = [ReviewImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('client', 'contractor', 'project', 'title', 'comment')
        }),
        ('Ratings', {
            'fields': (
                'rating', 'quality_rating', 'communication_rating',
                'timeliness_rating', 'professionalism_rating', 'average_category_rating'
            )
        }),
        ('Status', {
            'fields': ('is_verified', 'is_featured', 'is_public')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ReviewResponse)
class ReviewResponseAdmin(admin.ModelAdmin):
    list_display = ('review', 'contractor', 'created_at', 'updated_at')
    search_fields = (
        'review__title', 'review__comment', 'contractor__first_name', 
        'contractor__last_name', 'response_text'
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'is_helpful', 'created_at')
    list_filter = ('is_helpful', 'created_at')
    search_fields = ('review__title', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at',)