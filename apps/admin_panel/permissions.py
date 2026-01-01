from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from .models import AdminRole

User = get_user_model()


class AdminPermissionManager:
    """Менеджер для управления правами доступа администраторов"""
    
    ROLE_PERMISSIONS = {
        'superadmin': ['*'],  # Все права
        'admin': [
            'view_user', 'change_user', 'ban_user', 'unban_user',
            'view_content', 'moderate_content', 'approve_content', 'reject_content',
            'view_complaint', 'resolve_complaint', 'assign_complaint',
            'manage_email_templates', 'manage_banners',
            'send_notifications', 'send_push_notifications', 'send_email_campaigns',
            'view_analytics', 'export_analytics',
            'view_chats', 'send_system_messages', 'moderate_chats',
        ],
        'moderator': [
            'view_user', 'view_content', 'moderate_content', 'approve_content', 'reject_content',
            'view_complaint', 'resolve_complaint', 'view_analytics',
            'view_chats', 'send_system_messages', 'moderate_chats',
        ],
        'support': [
            'view_user', 'view_complaint', 'view_analytics', 'view_chats',
        ],
        'readonly': [
            'view_user', 'view_content', 'view_complaint', 'view_analytics', 'view_chats'
        ]
    }
    
    @classmethod
    def has_permission(cls, user, permission):
        """Проверка права доступа у пользователя"""
        if not user or not user.is_authenticated:
            return False
        
        try:
            admin_role = user.admin_role
            if not admin_role.is_active:
                return False
            
            if admin_role.role == 'superadmin':
                return True
            
            role_permissions = cls.ROLE_PERMISSIONS.get(admin_role.role, [])
            return '*' in role_permissions or permission in role_permissions
            
        except AttributeError:
            return False
    
    @classmethod
    def get_user_permissions(cls, user):
        """Получение списка прав пользователя"""
        if not user or not user.is_authenticated:
            return []
        
        try:
            admin_role = user.admin_role
            if not admin_role.is_active:
                return []
            
            return cls.ROLE_PERMISSIONS.get(admin_role.role, [])
            
        except AttributeError:
            return []
    
    @classmethod
    def require_permission(cls, user, permission):
        """Требование права доступа"""
        if not cls.has_permission(user, permission):
            raise PermissionDenied(f"Нет права доступа: {permission}")


class RoleManager:
    """Менеджер для управления ролями администраторов"""
    
    @staticmethod
    def assign_role(user, role, assigned_by=None):
        """Назначение роли пользователю"""
        if role not in AdminPermissionManager.ROLE_PERMISSIONS:
            raise ValueError(f"Неизвестная роль: {role}")
        
        with transaction.atomic():
            admin_role, created = AdminRole.objects.get_or_create(
                user=user,
                defaults={'role': role, 'created_by': assigned_by, 'is_active': True}
            )
            
            if not created:
                admin_role.role = role
                admin_role.is_active = True
                admin_role.save()
            
            return admin_role
    
    @staticmethod
    def remove_role(user):
        """Удаление роли у пользователя"""
        try:
            admin_role = user.admin_role
            admin_role.is_active = False
            admin_role.save()
        except AttributeError:
            pass
    
    @staticmethod
    def get_user_role(user):
        """Получение роли пользователя"""
        try:
            return user.admin_role.role if user.admin_role.is_active else None
        except AttributeError:
            return None