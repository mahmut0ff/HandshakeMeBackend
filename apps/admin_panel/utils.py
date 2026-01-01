"""
Утилиты для админ-панели
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def send_user_notification_email(user, template_type, context_data=None, override_email=None):
    """Отправляет уведомление пользователю"""
    try:
        from .tasks import send_notification_email
        
        recipient_email = override_email or user.email
        
        # Подготавливаем контекст
        default_context = {
            'user_name': user.get_full_name() or user.email,
            'user_email': user.email,
            'user_first_name': user.first_name,
            'user_last_name': user.last_name,
        }
        
        if context_data:
            default_context.update(context_data)
        
        # Отправляем через Celery
        send_notification_email.delay(
            template_type=template_type,
            recipient_email=recipient_email,
            context_data=default_context
        )
        
        logger.info(f'Уведомление {template_type} отправлено пользователю {user.email}')
        return True
        
    except Exception as e:
        logger.error(f'Ошибка отправки уведомления пользователю {user.email}: {str(e)}')
        return False


def send_content_moderation_notification(content_object, action, reason, admin_user):
    """Отправляет уведомление о модерации контента"""
    try:
        # Определяем автора контента
        author = None
        if hasattr(content_object, 'created_by'):
            author = content_object.created_by
        elif hasattr(content_object, 'user'):
            author = content_object.user
        elif hasattr(content_object, 'author'):
            author = content_object.author
        
        if not author:
            logger.warning(f'Не удалось определить автора для {content_object}')
            return False
        
        # Определяем тип шаблона на основе действия
        if action == 'approved':
            template_type = 'project_approved'  # или другой подходящий тип
        elif action == 'rejected':
            template_type = 'project_rejected'
        else:
            logger.warning(f'Неизвестное действие модерации: {action}')
            return False
        
        # Подготавливаем контекст
        context_data = {
            'content_type': content_object.__class__.__name__,
            'content_title': getattr(content_object, 'title', str(content_object)),
            'action': action,
            'reason': reason,
            'admin_name': admin_user.get_full_name() or admin_user.email,
            'moderation_date': timezone.now().strftime('%d.%m.%Y %H:%M'),
        }
        
        return send_user_notification_email(
            user=author,
            template_type=template_type,
            context_data=context_data
        )
        
    except Exception as e:
        logger.error(f'Ошибка отправки уведомления о модерации: {str(e)}')
        return False


def send_complaint_resolution_notification(complaint, resolution, admin_user):
    """Отправляет уведомление о решении жалобы"""
    try:
        context_data = {
            'complaint_id': str(complaint.id),
            'complaint_type': complaint.get_complaint_type_display(),
            'resolution': resolution,
            'admin_name': admin_user.get_full_name() or admin_user.email,
            'resolution_date': timezone.now().strftime('%d.%m.%Y %H:%M'),
        }
        
        return send_user_notification_email(
            user=complaint.complainant,
            template_type='complaint_resolved',
            context_data=context_data
        )
        
    except Exception as e:
        logger.error(f'Ошибка отправки уведомления о решении жалобы: {str(e)}')
        return False


def get_client_ip(request):
    """Получает IP адрес клиента"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_admin_action(admin_user, action, description, content_object=None, 
                    old_values=None, new_values=None, request=None):
    """Логирует действие администратора"""
    try:
        from .models import AdminActionLog
        
        ip_address = '127.0.0.1'
        if request:
            ip_address = get_client_ip(request)
        
        AdminActionLog.objects.create(
            admin_user=admin_user,
            action=action,
            description=description,
            content_object=content_object,
            old_values=old_values or {},
            new_values=new_values or {},
            ip_address=ip_address
        )
        
        logger.info(f'Действие администратора залогировано: {admin_user.email} - {action}')
        return True
        
    except Exception as e:
        logger.error(f'Ошибка логирования действия администратора: {str(e)}')
        return False


def validate_email_template(html_content):
    """Валидирует HTML контент email шаблона"""
    try:
        from bs4 import BeautifulSoup
        import re
        
        # Проверяем HTML синтаксис
        soup = BeautifulSoup(html_content, 'html.parser')
        
        errors = []
        warnings = []
        
        # Проверяем наличие обязательных элементов для email
        if not html_content.strip().startswith('<!DOCTYPE'):
            warnings.append('Рекомендуется добавить DOCTYPE для лучшей совместимости')
        
        if not soup.find('title'):
            warnings.append('Рекомендуется добавить тег <title>')
        
        if not soup.find('table'):
            warnings.append('Для лучшей совместимости с email клиентами рекомендуется использовать табличную верстку')
        
        # Проверяем переменные шаблона
        variables = re.findall(r'\{\{(\w+)\}\}', html_content)
        valid_variables = [
            'user_name', 'user_email', 'project_title', 'admin_name', 
            'site_name', 'site_url', 'current_date', 'current_time',
            'reason', 'resolution', 'complaint_id'
        ]
        
        invalid_variables = [var for var in variables if var not in valid_variables]
        if invalid_variables:
            errors.append(f'Неизвестные переменные: {", ".join(invalid_variables)}')
        
        # Проверяем CSS стили
        if soup.find('style') or soup.find('link', {'rel': 'stylesheet'}):
            warnings.append('Для лучшей совместимости рекомендуется использовать inline стили')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'variables_found': variables
        }
        
    except Exception as e:
        return {
            'valid': False,
            'errors': [f'Ошибка парсинга HTML: {str(e)}'],
            'warnings': []
        }


def format_file_size(size_bytes):
    """Форматирует размер файла в человекочитаемый вид"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def get_user_activity_summary(user, days=30):
    """Получает сводку активности пользователя"""
    from datetime import timedelta
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    summary = {
        'login_count': 0,
        'projects_created': 0,
        'messages_sent': 0,
        'last_activity': user.last_login,
    }
    
    try:
        # Подсчитываем входы
        from .models import AdminLoginLog
        summary['login_count'] = AdminLoginLog.objects.filter(
            user=user,
            timestamp__gte=start_date,
            success=True
        ).count()
        
        # Здесь можно добавить подсчет других активностей
        # summary['projects_created'] = Project.objects.filter(...)
        # summary['messages_sent'] = Message.objects.filter(...)
        
    except Exception as e:
        logger.error(f'Ошибка получения сводки активности для {user.email}: {str(e)}')
    
    return summary