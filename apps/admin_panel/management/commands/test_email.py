from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Тестирует отправку email'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email получателя', default='klovverg@gmail.com')

    def handle(self, *args, **options):
        email = options['email']
        
        self.stdout.write("=== ТЕСТ ОТПРАВКИ EMAIL ===")
        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        self.stdout.write(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        try:
            result = send_mail(
                subject='Тест отправки email из HandshakeMe',
                message='Это тестовое письмо для проверки настроек email.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            if result == 1:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Email успешно отправлен на {email}!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Ошибка отправки email')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Исключение при отправке: {str(e)}')
            )