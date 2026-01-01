import logging
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse, resolve
from django.contrib.auth import logout
from datetime import timedelta

from .models import AdminActionLog

logger = logging.getLogger(__name__)


class AdminPanelMiddleware:
    """
    Middleware для админ-панели с автоматическим логированием и проверкой сессий
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Проверяем, что это запрос к админ-панели
        if self.is_admin_panel_request(request):
            # Проверяем активность сессии
            if self.should_logout_inactive_session(request):
                logout(request)
                return HttpResponseRedirect(reverse('admin_panel:login'))
            
            # Обновляем время последней активности
            if request.user.is_authenticated:
                request.session['last_activity'] = timezone.now().isoformat()
        
        response = self.get_response(request)
        
        # Логируем действия после выполнения запроса
        if self.is_admin_panel_request(request) and request.user.is_authenticated:
            self.log_admin_action(request, response)
        
        return response
    
    def is_admin_panel_request(self, request):
        """Проверяем, является ли запрос запросом к админ-панели"""
        return request.path.startswith('/admin-panel/')
    
    def should_logout_inactive_session(self, request):
        """Проверяем, нужно ли завершить неактивную сессию"""
        if not request.user.is_authenticated:
            return False
        
        # Исключаем страницу логина
        if request.path == reverse('admin_panel:login'):
            return False
        
        last_activity_str = request.session.get('last_activity')
        if not last_activity_str:
            return False
        
        try:
            last_activity = timezone.datetime.fromisoformat(last_activity_str)
            if timezone.is_naive(last_activity):
                last_activity = timezone.make_aware(last_activity)
            
            # Проверяем, прошло ли 30 минут с последней активности
            inactive_time = timezone.now() - last_activity
            return inactive_time > timedelta(minutes=30)
        except (ValueError, TypeError):
            return False
    
    def log_admin_action(self, request, response):
        """Автоматическое логирование действий администраторов"""
        # Логируем только успешные запросы с изменениями данных
        if response.status_code >= 400:
            return
        
        # Логируем только POST, PUT, PATCH, DELETE запросы
        if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return
        
        try:
            # Определяем тип действия по методу и URL
            action_type = self.determine_action_type(request)
            description = self.generate_action_description(request)
            
            # Получаем IP адрес
            ip_address = self.get_client_ip(request)
            
            # Создаем лог
            AdminActionLog.objects.create(
                admin_user=request.user,
                action=action_type,
                description=description,
                ip_address=ip_address,
                old_values={},
                new_values={}
            )
            
        except Exception as e:
            logger.error(f"Ошибка автоматического логирования: {e}")
    
    def determine_action_type(self, request):
        """Определяем тип действия по HTTP методу и URL"""
        method_mapping = {
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete'
        }
        
        # Специальные случаи по URL
        if 'ban' in request.path:
            return 'ban'
        elif 'unban' in request.path:
            return 'unban'
        elif 'approve' in request.path:
            return 'approve'
        elif 'reject' in request.path:
            return 'reject'
        elif 'moderate' in request.path:
            return 'moderate'
        elif 'email' in request.path and request.method == 'POST':
            return 'email_send'
        elif 'settings' in request.path:
            return 'settings_change'
        
        return method_mapping.get(request.method, 'update')
    
    def generate_action_description(self, request):
        """Генерируем описание действия"""
        try:
            resolver_match = resolve(request.path)
            view_name = resolver_match.view_name
            
            # Базовое описание по имени view
            descriptions = {
                'admin_panel:user_action': 'Действие с пользователем',
                'admin_panel:complaint_detail': 'Работа с жалобой',
                'admin_panel:dashboard': 'Действие на дашборде',
            }
            
            return descriptions.get(view_name, f"Действие: {request.method} {request.path}")
            
        except Exception:
            return f"Действие: {request.method} {request.path}"
    
    def get_client_ip(self, request):
        """Получение IP адреса клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or '127.0.0.1'


class AdminSecurityMiddleware:
    """
    Middleware для дополнительной безопасности админ-панели
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Добавляем заголовки безопасности для админ-панели
        if request.path.startswith('/admin-panel/'):
            response = self.get_response(request)
            
            # Добавляем заголовки безопасности
            response['X-Frame-Options'] = 'DENY'
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            return response
        
        return self.get_response(request)