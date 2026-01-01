from django.contrib import admin
from .models import Category, Skill, ContractorProfile, Portfolio, PortfolioImage, Certification


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'category__name')


class PortfolioImageInline(admin.TabularInline):
    model = PortfolioImage
    extra = 1


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('title', 'contractor', 'category', 'project_date', 'is_featured', 'created_at')
    list_filter = ('category', 'is_featured', 'project_date', 'created_at')
    search_fields = ('title', 'contractor__user__first_name', 'contractor__user__last_name', 'contractor__business_name')
    inlines = [PortfolioImageInline]


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'contractor', 'issuing_organization', 'issue_date', 'expiry_date', 'is_verified')
    list_filter = ('is_verified', 'issue_date', 'expiry_date')
    search_fields = ('name', 'contractor__user__first_name', 'contractor__user__last_name', 'issuing_organization')


@admin.register(ContractorProfile)
class ContractorProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'business_name', 'experience_level', 'hourly_rate_min', 'hourly_rate_max',
        'rating_average', 'rating_count', 'availability_status', 'created_at'
    )
    list_filter = ('experience_level', 'availability_status', 'insurance_verified', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'business_name', 'license_number')
    filter_horizontal = ('categories', 'skills')
    readonly_fields = ('rating_average', 'rating_count', 'completed_projects')