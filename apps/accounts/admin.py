from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'user_type', 'is_verified', 'is_online', 'created_at')
    list_filter = ('user_type', 'is_verified', 'is_online', 'is_staff', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'user_type', 'avatar', 'bio', 'location', 'is_verified', 'is_online')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'first_name', 'last_name', 'phone_number', 'user_type')
        }),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'city', 'state', 'country', 'is_default', 'created_at')
    list_filter = ('country', 'state', 'is_default', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'title', 'city', 'state')
    ordering = ('-created_at',)