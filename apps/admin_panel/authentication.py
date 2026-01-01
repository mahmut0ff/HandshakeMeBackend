from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

from .models import AdminRole, AdminLoginLog

User = get_user_model()
logger = logging.getLogger(__name__)


class AdminAuthenticationBackend(BaseBackend):
    """
    Кастомный backend для аутентификации администраторов
    с ограничением попыток входа и логированием
    """
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        """
        Аутентификация администратора с проверкой прав и ограничением попыток
        """
        if not email or not password:
            return None
        
        # Получаем IP адрес для ограничения попыток
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Проверяем ограничения по IP
        if self.is_ip_blocked(ip_address):
            self.log_failed_attempt(None, ip_address, user_agent, "IP заблокирован")
            return None
        
        try:
            # Ищем пользователя по email
            user = User.objects.get(email=email)
            
            # Проверяем пароль
            if not user.check_password(password):
                self.handle_failed_attempt(user, ip_address, user_agent, "Неверный пароль")
                return None
            
            # Проверяем, что пользователь активен
            if not user.is_active:
                self.log_failed_attempt(user, ip_address, user_agent, "Пользователь неактивен")
                return None
            
            # Проверяем, что у пользователя есть админская роль
            if not self.has_admin_role(user):
                self.log_failed_attempt(user, ip_address, user_agent, "Нет админских прав")
                return None
            
            # Проверяем, что роль активна
            if not self.is_admin_role_active(user):
                self.log_failed_attempt(user, ip_address, user_agent, "Админская роль неактивна")
                return None
            
            # Успешная аутентификация
            self.log_successful_attempt(user, ip_address, user_agent)
            self.clear_failed_attempts(ip_address)
            
            return user
            
        except User.DoesNotExist:
            self.handle_failed_attempt(None, ip_address, user_agent, "Пользователь не найден")
            return None
        except Exception as e:
            logger.error(f"Ошибка аутентификации: {e}")
            self.log_failed_attempt(None, ip_address, user_agent, f"Системная ошибка: {str(e)}")
            return None
    
    def get_user(self, user_id):
        """
        Получение пользователя по ID с проверкой админских прав
        """
        try:
            user = User.objects.get(pk=user_id)
            if self.has_admin_role(user) and self.is_admin_role_active(user):
                return user
        except User.DoesNotExist:
            pass
        return None
    
    def has_admin_role(self, user):
        """
        Проверка наличия админской роли у пользователя
        """
        try:
            return hasattr(user, 'admin_role') and user.admin_role is not None
        except:
            return False
    
    def is_admin_role_active(self, user):
        """
        Проверка активности админской роли
        """
        try:
            return user.admin_role.is_active
        except:
            return False
    
    def get_client_ip(self, request):
        """
        Получение IP адреса клиента
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_ip_blocked(self, ip_address):
        """
        Проверка, заблокирован ли IP адрес
        """
        cache_key = f"admin_login_attempts_{ip_address}"
        attempts = cache.get(cache_key, 0)
        return attempts >= 5
    
    def handle_failed_attempt(self, user, ip_address, user_agent, reason):
        """
        Обработка неудачной попытки входа
        """
        # Логируем попытку
        self.log_failed_attempt(user, ip_address, user_agent, reason)
        
        # Увеличиваем счетчик попыток для IP
        cache_key = f"admin_login_attempts_{ip_address}"
        attempts = cache.get(cache_key, 0) + 1
        cache.set(cache_key, attempts, timeout=600)  # 10 минут
        
        logger.warning(f"Неудачная попытка входа в админ-панель: {reason}, IP: {ip_address}, попытка {attempts}/5")
    
    def clear_failed_attempts(self, ip_address):
        """
        Очистка счетчика неудачных попыток для IP
        """
        cache_key = f"admin_login_attempts_{ip_address}"
        cache.delete(cache_key)
    
    def log_successful_attempt(self, user, ip_address, user_agent):
        """
        Логирование успешной попытки входа
        """
        try:
            AdminLoginLog.objects.create(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True
            )
            logger.info(f"Успешный вход в админ-панель: {user.email}, IP: {ip_address}")
        except Exception as e:
            logger.error(f"Ошибка логирования успешного входа: {e}")
    
    def log_failed_attempt(self, user, ip_address, user_agent, reason):
        """
        Логирование неудачной попытки входа
        """
        try:
            AdminLoginLog.objects.create(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason=reason
            )
        except Exception as e:
            logger.error(f"Ошибка логирования неудачного входа: {e}")


class AdminPermissionMixin:
    """
    Mixin для проверки прав доступа администраторов
    """
    
    def has_admin_permission(self, user, permission=None):
        """
        Проверка прав доступа администратора
        """
        if not user or not user.is_authenticated:
            return False
        
        try:
            admin_role = user.admin_role
            if not admin_role.is_active:
                return False
            
            # SuperAdmin имеет все права
            if admin_role.role == 'superadmin':
                return True
            
            # Проверяем конкретное право
            if permission:
                return self.check_role_permission(admin_role.role, permission)
            
            return True
            
        except AttributeError:
            return False
    
    def check_role_permission(self, role, permission):
        """
        Проверка права для конкретной роли
        """
        # Матрица прав доступа
        ROLE_PERMISSIONS = {
            'superadmin': ['*'],  # Все права
            'admin': [
                'view_user', 'change_user', 'ban_user',
                'view_content', 'moderate_content',
                'view_complaint', 'resolve_complaint',
                'manage_settings', 'send_notifications',
                'view_analytics', 'manage_email_templates',
                'manage_banners', 'send_push_notifications'
            ],
            'moderator': [
                'view_user', 'view_content', 'moderate_content',
                'view_complaint', 'resolve_complaint',
                'view_analytics'
            ],
            'support': [
                'view_user', 'view_complaint', 'view_analytics'
            ],
            'readonly': [
                'view_user', 'view_content', 'view_complaint',
                'view_analytics'
            ]
        }
        
        role_permissions = ROLE_PERMISSIONS.get(role, [])
        return '*' in role_permissions or permission in role_permissions
    
    def get_user_role(self, user):
        """
        Получение роли пользователя
        """
        try:
            return user.admin_role.role
        except AttributeError:
            return None


def get_admin_role_display(role):
    """
    Получение отображаемого названия роли
    """
    role_names = {
        'superadmin': 'Суперадминистратор',
        'admin': 'Администратор',
        'moderator': 'Модератор',
        'support': 'Поддержка',
        'readonly': 'Только чтение'
    }
    return role_names.get(role, role)


def get_role_permissions(role):
    """
    Получение списка прав для роли
    """
    ROLE_PERMISSIONS = {
        'superadmin': [
            'Полный доступ ко всем функциям',
            'Управление администраторами',
            'Системные настройки',
            'Экспорт/импорт данных'
        ],
        'admin': [
            'Управление пользователями',
            'Модерация контента',
            'Обработка жалоб',
            'Email рассылки',
            'Push уведомления',
            'Управление баннерами',
            'Просмотр аналитики'
        ],
        'moderator': [
            'Просмотр пользователей',
            'Модерация контента',
            'Обработка жалоб',
            'Просмотр аналитики'
        ],
        'support': [
            'Просмотр пользователей',
            'Просмотр жалоб',
            'Просмотр аналитики'
        ],
        'readonly': [
            'Только просмотр данных',
            'Без права изменений'
        ]
    }
    return ROLE_PERMISSIONS.get(role, [])