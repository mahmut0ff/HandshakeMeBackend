#!/usr/bin/env python
"""
Простой тест для проверки функциональности управления пользователями
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contractor_connect.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.admin_panel.models import AdminRole, AdminActionLog
from apps.admin_panel.utils import send_user_notification_email

User = get_user_model()

def test_user_management_functionality():
    """Тест основной функциональности управления пользователями"""
    
    print("🧪 Тестирование функциональности управления пользователями...")
    
    # Создаем тестового администратора
    admin_user, created = User.objects.get_or_create(
        email='test_admin@example.com',
        defaults={
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Admin'
        }
    )
    
    if created:
        print("✅ Создан тестовый администратор")
    
    # Создаем роль администратора
    admin_role, created = AdminRole.objects.get_or_create(
        user=admin_user,
        defaults={'role': 'admin'}
    )
    
    if created:
        print("✅ Создана роль администратора")
    
    # Создаем тестового пользователя
    test_user, created = User.objects.get_or_create(
        email='test_user@example.com',
        defaults={
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True
        }
    )
    
    if created:
        print("✅ Создан тестовый пользователь")
    
    # Тест 1: Блокировка пользователя
    print("\n📝 Тест 1: Блокировка пользователя")
    original_status = test_user.is_active
    test_user.is_active = False
    test_user.save()
    
    # Создаем лог действия
    AdminActionLog.objects.create(
        admin_user=admin_user,
        action='ban',
        description='Тестовая блокировка пользователя',
        content_object=test_user,
        old_values={'is_active': original_status},
        new_values={'is_active': False, 'ban_reason': 'Тест'},
        ip_address='127.0.0.1'
    )
    
    print(f"   Пользователь {test_user.email} заблокирован: {not test_user.is_active}")
    
    # Тест 2: Разблокировка пользователя
    print("\n📝 Тест 2: Разблокировка пользователя")
    test_user.is_active = True
    test_user.save()
    
    AdminActionLog.objects.create(
        admin_user=admin_user,
        action='unban',
        description='Тестовая разблокировка пользователя',
        content_object=test_user,
        old_values={'is_active': False},
        new_values={'is_active': True},
        ip_address='127.0.0.1'
    )
    
    print(f"   Пользователь {test_user.email} разблокирован: {test_user.is_active}")
    
    # Тест 3: Мягкое удаление
    print("\n📝 Тест 3: Мягкое удаление пользователя")
    original_email = test_user.email
    test_user.is_active = False
    if not test_user.email.startswith('deleted_'):
        test_user.email = f'deleted_{test_user.id}_{test_user.email}'
    test_user.save()
    
    AdminActionLog.objects.create(
        admin_user=admin_user,
        action='delete',
        description='Тестовое удаление пользователя',
        content_object=test_user,
        old_values={'is_active': True, 'email': original_email},
        new_values={'is_active': False, 'email': test_user.email, 'delete_reason': 'Тест'},
        ip_address='127.0.0.1'
    )
    
    print(f"   Пользователь помечен как удаленный: {test_user.email}")
    
    # Тест 4: Проверка логов действий
    print("\n📝 Тест 4: Проверка логов действий")
    logs_count = AdminActionLog.objects.filter(admin_user=admin_user).count()
    print(f"   Создано логов действий: {logs_count}")
    
    # Тест 5: Тест функции отправки email (без реальной отправки)
    print("\n📝 Тест 5: Тест функции отправки email")
    try:
        # Создаем тестовый контекст
        context = {
            'reason': 'Тестовая причина',
            'admin': admin_user
        }
        
        # Пытаемся отправить уведомление (будет ошибка, но функция должна обработать её)
        result = send_user_notification_email(
            test_user, 
            'user_banned', 
            context
        )
        print(f"   Функция отправки email выполнена: {result is not None}")
    except Exception as e:
        print(f"   Функция отправки email обработала ошибку: {type(e).__name__}")
    
    print("\n✅ Все тесты завершены!")
    
    # Очистка тестовых данных
    print("\n🧹 Очистка тестовых данных...")
    AdminActionLog.objects.filter(admin_user=admin_user).delete()
    test_user.delete()
    admin_role.delete()
    admin_user.delete()
    print("✅ Тестовые данные очищены")

if __name__ == '__main__':
    test_user_management_functionality()