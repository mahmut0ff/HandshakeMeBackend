from django.core.management.base import BaseCommand
from django.core.mail import get_connection
from django.conf import settings
import smtplib
import socket

class Command(BaseCommand):
    help = 'Диагностирует настройки email'

    def handle(self, *args, **options):
        self.stdout.write("=== ДИАГНОСТИКА EMAIL НАСТРОЕК ===")
        
        # Проверяем настройки Django
        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        self.stdout.write(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"EMAIL_HOST_PASSWORD: {'***' if settings.EMAIL_HOST_PASSWORD else 'НЕ УСТАНОВЛЕН'}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        # Проверяем подключение к SMTP серверу
        self.stdout.write("\n=== ПРОВЕРКА ПОДКЛЮЧЕНИЯ К SMTP ===")
        try:
            # Проверяем доступность хоста
            socket.create_connection((settings.EMAIL_HOST, settings.EMAIL_PORT), timeout=10)
            self.stdout.write(self.style.SUCCESS(f"✅ Хост {settings.EMAIL_HOST}:{settings.EMAIL_PORT} доступен"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Не удается подключиться к {settings.EMAIL_HOST}:{settings.EMAIL_PORT}: {e}"))
            return
        
        # Проверяем SMTP аутентификацию
        try:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.quit()
            self.stdout.write(self.style.SUCCESS("✅ SMTP аутентификация успешна"))
        except smtplib.SMTPAuthenticationError as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка аутентификации SMTP: {e}"))
            self.stdout.write("Возможные причины:")
            self.stdout.write("1. Неверный пароль")
            self.stdout.write("2. Нужно использовать App Password для Gmail")
            self.stdout.write("3. Двухфакторная аутентификация не настроена")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка SMTP: {e}"))
        
        # Проверяем Django email backend
        self.stdout.write("\n=== ПРОВЕРКА DJANGO EMAIL BACKEND ===")
        try:
            connection = get_connection()
            connection.open()
            self.stdout.write(self.style.SUCCESS("✅ Django email backend работает"))
            connection.close()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка Django email backend: {e}"))