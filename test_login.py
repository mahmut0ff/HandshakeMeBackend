#!/usr/bin/env python
"""
Тест входа в админ-панель
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contractor_connect.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

def test_admin_login():
    """Тест входа в админ-панель"""
    
    print("🧪 Тестирование входа в админ-панель...")
    
    client = Client()
    
    # Тестируем GET запрос к странице входа
    print("\n1. Тестируем доступ к странице входа...")
    response = client.get('/admin-panel/login/')
    print(f"   Статус: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ Страница входа доступна")
    else:
        print("   ❌ Страница входа недоступна")
        return
    
    # Тестируем POST запрос с правильными данными
    print("\n2. Тестируем вход с правильными данными...")
    login_data = {
        'email': 'admin@handshakeme.com',
        'password': 'admin123',
        'remember_me': False
    }
    
    response = client.post('/admin-panel/login/', login_data, follow=True)
    print(f"   Статус: {response.status_code}")
    print(f"   URL после редиректа: {response.request['PATH_INFO']}")
    
    if '/admin-panel/' in response.request['PATH_INFO'] and response.status_code == 200:
        print("   ✅ Вход успешен!")
    else:
        print("   ❌ Вход не удался")
        print(f"   Содержимое ответа: {response.content.decode()[:500]}...")
    
    # Проверяем, что пользователь аутентифицирован
    if hasattr(response, 'wsgi_request') and response.wsgi_request.user.is_authenticated:
        print(f"   ✅ Пользователь аутентифицирован: {response.wsgi_request.user.email}")
    else:
        print("   ❌ Пользователь не аутентифицирован")

if __name__ == '__main__':
    test_admin_login()