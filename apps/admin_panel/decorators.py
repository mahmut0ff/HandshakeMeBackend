from functools import wraps
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View

from .authentication import AdminPermissionMixin


def admin_required(permissions=None):
    """
    Декоратор для проверки админских прав
    
    Args:
        permissions: список требуемых прав или одно право (строка)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Проверяем аутентификацию
            if not request.user.is_authenticated:
                return HttpResponseRedirect(reverse('admin_panel:login'))
            
            # Проверяем админские права
            permission_mixin = AdminPermissionMixin()
            
            if isinstance(permissions, str):
                required_permissions = [permissions]
            elif isinstance(permissions, list):
                required_permissions = permissions
            else:
                required_permissions = []
            
            # Если права не указаны, проверяем только наличие админской роли
            if not required_permissions:
                if not permission_mixin.has_admin_permission(request.user):
                    return render(request, 'admin_panel/errors/403.html', {
                        'error_message': 'У вас нет прав доступа к админ-панели'
                    }, status=403)
            else:
                # Проверяем каждое требуемое право
                for permission in required_permissions:
                    if not permission_mixin.has_admin_permission(request.user, permission):
                        return render(request, 'admin_panel/errors/403.html', {
                            'error_message': f'У вас нет права: {permission}'
                        }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def superadmin_required(view_func):
    """
    Декоратор для проверки прав суперадминистратора
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('admin_panel:login'))
        
        try:
            if request.user.admin_role.role != 'superadmin':
                return render(request, 'admin_panel/errors/403.html', {
                    'error_message': 'Доступ только для суперадминистраторов'
                }, status=403)
        except AttributeError:
            return render(request, 'admin_panel/errors/403.html', {
                'error_message': 'У вас нет прав доступа к админ-панели'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(required_roles):
    """
    Декоратор для проверки конкретных ролей
    
    Args:
        required_roles: список ролей или одна роль (строка)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseRedirect(reverse('admin_panel:login'))
            
            if isinstance(required_roles, str):
                roles = [required_roles]
            else:
                roles = required_roles
            
            try:
                user_role = request.user.admin_role.role
                if user_role not in roles:
                    return render(request, 'admin_panel/errors/403.html', {
                        'error_message': f'Доступ только для ролей: {", ".join(roles)}'
                    }, status=403)
            except AttributeError:
                return render(request, 'admin_panel/errors/403.html', {
                    'error_message': 'У вас нет прав доступа к админ-панели'
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class AdminRequiredMixin(AdminPermissionMixin):
    """
    Mixin для Class-Based Views с проверкой админских прав
    """
    required_permissions = None
    required_roles = None
    
    def dispatch(self, request, *args, **kwargs):
        # Проверяем аутентификацию
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('admin_panel:login'))
        
        # Проверяем админские права
        if not self.has_admin_permission(request.user):
            return render(request, 'admin_panel/errors/403.html', {
                'error_message': 'У вас нет прав доступа к админ-панели'
            }, status=403)
        
        # Проверяем конкретные роли
        if self.required_roles:
            try:
                user_role = request.user.admin_role.role
                if isinstance(self.required_roles, str):
                    roles = [self.required_roles]
                else:
                    roles = self.required_roles
                
                if user_role not in roles:
                    return render(request, 'admin_panel/errors/403.html', {
                        'error_message': f'Доступ только для ролей: {", ".join(roles)}'
                    }, status=403)
            except AttributeError:
                return render(request, 'admin_panel/errors/403.html', {
                    'error_message': 'У вас нет прав доступа к админ-панели'
                }, status=403)
        
        # Проверяем конкретные права
        if self.required_permissions:
            if isinstance(self.required_permissions, str):
                permissions = [self.required_permissions]
            else:
                permissions = self.required_permissions
            
            for permission in permissions:
                if not self.has_admin_permission(request.user, permission):
                    return render(request, 'admin_panel/errors/403.html', {
                        'error_message': f'У вас нет права: {permission}'
                    }, status=403)
        
        return super().dispatch(request, *args, **kwargs)


class SuperAdminRequiredMixin:
    """
    Mixin для Class-Based Views с проверкой прав суперадминистратора
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('admin_panel:login'))
        
        try:
            if request.user.admin_role.role != 'superadmin':
                return render(request, 'admin_panel/errors/403.html', {
                    'error_message': 'Доступ только для суперадминистраторов'
                }, status=403)
        except AttributeError:
            return render(request, 'admin_panel/errors/403.html', {
                'error_message': 'У вас нет прав доступа к админ-панели'
            }, status=403)
        
        return super().dispatch(request, *args, **kwargs)


def log_admin_action(action_type, description, content_object=None, old_values=None, new_values=None):
    """
    Декоратор для логирования действий администраторов
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Выполняем основную функцию
            response = view_func(request, *args, **kwargs)
            
            # Логируем действие только при успешном выполнении
            if hasattr(response, 'status_code') and response.status_code < 400:
                try:
                    from .models import AdminActionLog
                    from django.contrib.contenttypes.models import ContentType
                    
                    # Получаем IP адрес
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    if x_forwarded_for:
                        ip_address = x_forwarded_for.split(',')[0]
                    else:
                        ip_address = request.META.get('REMOTE_ADDR')
                    
                    # Создаем лог
                    log_data = {
                        'admin_user': request.user,
                        'action': action_type,
                        'description': description,
                        'ip_address': ip_address,
                        'old_values': old_values or {},
                        'new_values': new_values or {}
                    }
                    
                    if content_object:
                        log_data['content_type'] = ContentType.objects.get_for_model(content_object)
                        log_data['object_id'] = content_object.pk
                    
                    AdminActionLog.objects.create(**log_data)
                    
                except Exception as e:
                    # Не прерываем выполнение из-за ошибки логирования
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Ошибка логирования действия администратора: {e}")
            
            return response
        return wrapper
    return decorator


# Готовые декораторы для частых случаев
view_users_required = admin_required('view_user')
manage_users_required = admin_required(['view_user', 'change_user'])
moderate_content_required = admin_required('moderate_content')
resolve_complaints_required = admin_required('resolve_complaint')
manage_settings_required = admin_required('manage_settings')
send_notifications_required = admin_required('send_notifications')
view_analytics_required = admin_required('view_analytics')