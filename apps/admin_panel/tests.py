from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import Group, Permission
from django.core import mail
from unittest.mock import patch
import json
from .models import AdminRole, AdminLoginLog, AdminActionLog, Complaint
from .permissions import AdminPermissionManager, RoleManager

User = get_user_model()


class UserManagementActionsTest(TestCase):
    """Тесты действий с пользователями"""
    
    def setUp(self):
        self.client = Client()
        
        # Создаем администратора
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        AdminRole.objects.create(user=self.admin_user, role='admin')
        
        # Создаем обычного пользователя для тестирования действий
        self.target_user = User.objects.create_user(
            email='target@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Логинимся как администратор
        self.client.login(email='admin@test.com', password='testpass123')
    
    def test_user_ban_success(self):
        """Тест успешной блокировки пользователя"""
        self.assertTrue(self.target_user.is_active)
        
        response = self.client.post(
            reverse('admin_panel:user_ban', args=[self.target_user.id]),
            {'reason': 'Нарушение правил'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Проверяем, что пользователь заблокирован
        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)
        
        # Проверяем, что создался лог действия
        self.assertTrue(AdminActionLog.objects.filter(
            admin_user=self.admin_user,
            action='ban',
            content_type__model='user',
            object_id=self.target_user.id
        ).exists())
    
    def test_user_unban_success(self):
        """Тест успешной разблокировки пользователя"""
        # Сначала блокируем пользователя
        self.target_user.is_active = False
        self.target_user.save()
        
        response = self.client.post(
            reverse('admin_panel:user_unban', args=[self.target_user.id])
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Проверяем, что пользователь разблокирован
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.is_active)
        
        # Проверяем, что создался лог действия
        self.assertTrue(AdminActionLog.objects.filter(
            admin_user=self.admin_user,
            action='unban',
            content_type__model='user',
            object_id=self.target_user.id
        ).exists())
    
    def test_user_soft_delete_success(self):
        """Тест успешного мягкого удаления пользователя"""
        original_email = self.target_user.email
        
        response = self.client.post(
            reverse('admin_panel:user_delete', args=[self.target_user.id]),
            {'reason': 'Запрос пользователя'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Проверяем, что пользователь помечен как удаленный
        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)
        self.assertTrue(self.target_user.email.startswith('deleted_'))
        self.assertIn(original_email, self.target_user.email)
        
        # Проверяем, что создался лог действия
        self.assertTrue(AdminActionLog.objects.filter(
            admin_user=self.admin_user,
            action='delete',
            content_type__model='user',
            object_id=self.target_user.id
        ).exists())
    
    def test_user_ban_without_reason_fails(self):
        """Тест блокировки без указания причины"""
        response = self.client.post(
            reverse('admin_panel:user_ban', args=[self.target_user.id]),
            {'reason': ''}
        )
        
        # Пользователь должен остаться активным
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.is_active)
    
    def test_user_actions_require_admin_permissions(self):
        """Тест что действия требуют прав администратора"""
        # Создаем пользователя без прав
        regular_user = User.objects.create_user(
            email='regular@test.com',
            password='testpass123'
        )
        
        client = Client()
        client.login(email='regular@test.com', password='testpass123')
        
        # Пытаемся заблокировать пользователя
        response = client.post(
            reverse('admin_panel:user_ban', args=[self.target_user.id]),
            {'reason': 'Test'}
        )
        
        # Должен быть редирект на страницу входа или ошибка доступа
        self.assertIn(response.status_code, [302, 403])
    
    @patch('apps.admin_panel.utils.send_user_notification_email')
    def test_email_notification_sent_on_ban(self, mock_send_email):
        """Тест отправки email уведомления при блокировке"""
        mock_send_email.return_value = True
        
        response = self.client.post(
            reverse('admin_panel:user_ban', args=[self.target_user.id]),
            {'reason': 'Нарушение правил'}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что функция отправки email была вызвана
        mock_send_email.assert_called_once_with(
            self.target_user,
            'user_banned',
            {'reason': 'Нарушение правил', 'admin': self.admin_user}
        )
    
    @patch('apps.admin_panel.utils.send_user_notification_email')
    def test_email_notification_sent_on_unban(self, mock_send_email):
        """Тест отправки email уведомления при разблокировке"""
        mock_send_email.return_value = True
        
        # Сначала блокируем пользователя
        self.target_user.is_active = False
        self.target_user.save()
        
        response = self.client.post(
            reverse('admin_panel:user_unban', args=[self.target_user.id])
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что функция отправки email была вызвана
        mock_send_email.assert_called_once_with(
            self.target_user,
            'user_unbanned',
            {'admin': self.admin_user}
        )
    
    @patch('apps.admin_panel.utils.send_user_notification_email')
    def test_email_notification_sent_on_delete(self, mock_send_email):
        """Тест отправки email уведомления при удалении"""
        mock_send_email.return_value = True
        original_email = self.target_user.email
        
        response = self.client.post(
            reverse('admin_panel:user_delete', args=[self.target_user.id]),
            {'reason': 'Запрос пользователя'}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что функция отправки email была вызвана с оригинальным email
        mock_send_email.assert_called_once_with(
            self.target_user,
            'user_deleted',
            {'reason': 'Запрос пользователя', 'admin': self.admin_user},
            override_email=original_email
        )
    
    def test_user_detail_page_shows_action_buttons(self):
        """Тест отображения кнопок действий на странице пользователя"""
        response = self.client.get(
            reverse('admin_panel:user_detail', args=[self.target_user.id])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Заблокировать')
        self.assertContains(response, 'Удалить')
        self.assertContains(response, 'showBanModal()')
        self.assertContains(response, 'showDeleteModal()')
    
    def test_user_detail_page_shows_unban_for_inactive_user(self):
        """Тест отображения кнопки разблокировки для заблокированного пользователя"""
        self.target_user.is_active = False
        self.target_user.save()
        
        response = self.client.get(
            reverse('admin_panel:user_detail', args=[self.target_user.id])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Разблокировать')
        self.assertContains(response, 'unbanUser()')
        self.assertNotContains(response, 'Заблокировать')


class AdminPanelPermissionsTest(TestCase):
    """Тесты системы прав доступа"""
    
    def setUp(self):
        self.superuser = User.objects.create_user(
            email='superuser@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        
        self.moderator_user = User.objects.create_user(
            email='moderator@test.com',
            password='testpass123'
        )
        
        self.regular_user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        
        # Создаем роли
        AdminRole.objects.create(user=self.admin_user, role='admin')
        AdminRole.objects.create(user=self.moderator_user, role='moderator')
    
    def test_superuser_has_all_permissions(self):
        """Суперпользователь имеет все права"""
        self.assertTrue(AdminPermissionManager.has_permission(self.superuser, 'view_user'))
        self.assertTrue(AdminPermissionManager.has_permission(self.superuser, 'manage_settings'))
        self.assertTrue(AdminPermissionManager.has_permission(self.superuser, 'moderate_content'))
    
    def test_admin_role_permissions(self):
        """Тест прав администратора"""
        self.assertTrue(AdminPermissionManager.has_permission(self.admin_user, 'view_user'))
        self.assertTrue(AdminPermissionManager.has_permission(self.admin_user, 'moderate_content'))
        self.assertFalse(AdminPermissionManager.has_permission(self.admin_user, 'manage_system_settings'))
    
    def test_moderator_role_permissions(self):
        """Тест прав модератора"""
        self.assertTrue(AdminPermissionManager.has_permission(self.moderator_user, 'moderate_content'))
        self.assertFalse(AdminPermissionManager.has_permission(self.moderator_user, 'ban_user'))
        self.assertFalse(AdminPermissionManager.has_permission(self.moderator_user, 'manage_settings'))
    
    def test_regular_user_no_admin_permissions(self):
        """Обычный пользователь не имеет прав администратора"""
        self.assertFalse(AdminPermissionManager.has_permission(self.regular_user, 'moderate_content'))
        self.assertFalse(AdminPermissionManager.has_permission(self.regular_user, 'view_user'))
        self.assertFalse(AdminPermissionManager.has_permission(self.regular_user, 'manage_settings'))
    
    def test_get_user_admin_role(self):
        """Тест получения роли пользователя"""
        self.assertEqual(RoleManager.get_user_role(self.admin_user), 'admin')
        self.assertEqual(RoleManager.get_user_role(self.moderator_user), 'moderator')
        self.assertIsNone(RoleManager.get_user_role(self.regular_user))


class AdminPanelViewsTest(TestCase):
    """Тесты представлений админ-панели"""
    
    def setUp(self):
        self.client = Client()
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        AdminRole.objects.create(user=self.admin_user, role='admin')
        
        self.regular_user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
    
    def test_admin_login_required(self):
        """Тест требования авторизации для админ-панели"""
        response = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(response.status_code, 302)  # Редирект на логин
    
    def test_admin_login_success(self):
        """Тест успешного входа администратора"""
        response = self.client.post(reverse('admin_panel:login'), {
            'username': 'admin@test.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Редирект на дашборд
        
        # Проверяем, что создался лог входа
        self.assertTrue(AdminLoginLog.objects.filter(
            user=self.admin_user,
            success=True
        ).exists())
    
    def test_admin_login_failure(self):
        """Тест неудачного входа"""
        response = self.client.post(reverse('admin_panel:login'), {
            'username': 'admin@test.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # Остается на странице логина
        
        # Проверяем, что создался лог неудачного входа
        self.assertTrue(AdminLoginLog.objects.filter(
            user=self.admin_user,
            success=False
        ).exists())
    
    def test_regular_user_cannot_access_admin(self):
        """Обычный пользователь не может войти в админ-панель"""
        response = self.client.post(reverse('admin_panel:login'), {
            'username': 'user@test.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 200)  # Остается на странице логина
        self.assertContains(response, 'У вас нет прав доступа к админ-панели')
    
    def test_dashboard_access(self):
        """Тест доступа к дашборду"""
        self.client.login(username='admin@test.com', password='testpass123')
        response = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Дашборд')
    
    def test_users_list_access(self):
        """Тест доступа к списку пользователей"""
        self.client.login(username='admin@test.com', password='testpass123')
        response = self.client.get(reverse('admin_panel:users_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Пользователи системы')


class AdminModelsTest(TestCase):
    """Тесты моделей админ-панели"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
    
    def test_admin_role_creation(self):
        """Тест создания роли администратора"""
        role = AdminRole.objects.create(
            user=self.admin_user,
            role='admin',
            created_by=self.user
        )
        
        self.assertEqual(role.user, self.admin_user)
        self.assertEqual(role.role, 'admin')
        self.assertTrue(role.is_active)
        self.assertEqual(str(role), f"{self.admin_user.email} - Admin")
    
    def test_admin_login_log_creation(self):
        """Тест создания лога входа"""
        log = AdminLoginLog.objects.create(
            user=self.admin_user,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            success=True
        )
        
        self.assertEqual(log.user, self.admin_user)
        self.assertTrue(log.success)
        self.assertIn('Успешно', str(log))
    
    def test_admin_action_log_creation(self):
        """Тест создания лога действий"""
        log = AdminActionLog.objects.create(
            admin_user=self.admin_user,
            action='ban',
            description='Пользователь заблокирован',
            ip_address='127.0.0.1'
        )
        
        self.assertEqual(log.admin_user, self.admin_user)
        self.assertEqual(log.action, 'ban')
        self.assertIn('Блокировка', str(log))
    
    def test_complaint_creation(self):
        """Тест создания жалобы"""
        from django.contrib.contenttypes.models import ContentType
        
        complaint = Complaint.objects.create(
            complainant=self.user,
            content_type=ContentType.objects.get_for_model(User),
            object_id=self.admin_user.id,
            complaint_type='spam',
            description='Спам в сообщениях'
        )
        
        self.assertEqual(complaint.complainant, self.user)
        self.assertEqual(complaint.complaint_type, 'spam')
        self.assertEqual(complaint.status, 'pending')
        self.assertIn('Спам', str(complaint))


class AdminFormsTest(TestCase):
    """Тесты форм админ-панели"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123'
        )
    
    def test_admin_login_form_valid(self):
        """Тест валидной формы входа"""
        from .forms import AdminLoginForm
        from django.test import RequestFactory
        
        AdminRole.objects.create(user=self.user, role='admin')
        
        factory = RequestFactory()
        request = factory.post('/admin-panel/login/')
        
        form = AdminLoginForm(request, data={
            'username': 'test@test.com',
            'password': 'testpass123'
        })
        
        self.assertTrue(form.is_valid())
    
    def test_admin_login_form_invalid_no_role(self):
        """Тест формы входа для пользователя без роли администратора"""
        from .forms import AdminLoginForm
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.post('/admin-panel/login/')
        
        form = AdminLoginForm(request, data={
            'username': 'test@test.com',
            'password': 'testpass123'
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('У вас нет прав доступа к админ-панели', str(form.errors))
    
    def test_user_search_form(self):
        """Тест формы поиска пользователей"""
        from .forms import UserSearchForm
        
        form = UserSearchForm(data={
            'search': 'test',
            'user_type': 'client',
            'is_active': 'true'
        })
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['search'], 'test')
        self.assertEqual(form.cleaned_data['user_type'], 'client')
        self.assertEqual(form.cleaned_data['is_active'], 'true')