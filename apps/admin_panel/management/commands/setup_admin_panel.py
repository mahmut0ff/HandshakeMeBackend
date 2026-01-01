from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.admin_panel.models import AdminRole, SystemSettings, EmailTemplate, MessageTemplate

User = get_user_model()


class Command(BaseCommand):
    help = 'Настройка админ-панели: создание суперадмина и базовых настроек'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email суперадминистратора',
            default='admin@handshakeme.com'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Пароль суперадминистратора',
            default='admin123'
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write('Настройка админ-панели HandshakeMe...')
            
            # Создаем суперадминистратора
            self.create_superadmin(options['email'], options['password'])
            
            # Создаем базовые настройки
            self.create_system_settings()
            
            self.stdout.write(
                self.style.SUCCESS('Админ-панель успешно настроена!')
            )
            
            self.stdout.write(f'Email: {options["email"]}')
            self.stdout.write(f'Пароль: {options["password"]}')
            self.stdout.write('URL: http://localhost:8000/admin-panel/')

    def create_superadmin(self, email, password):
        """Создание суперадминистратора"""
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f'Пользователь {email} уже существует')
        except User.DoesNotExist:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name='Super',
                last_name='Admin',
                is_active=True
            )
            self.stdout.write(f'Создан пользователь: {email}')
        
        # Назначаем роль суперадминистратора
        admin_role, created = AdminRole.objects.get_or_create(
            user=user,
            defaults={
                'role': 'superadmin',
                'is_active': True,
                'created_by': user
            }
        )
        
        if created:
            self.stdout.write('Назначена роль суперадминистратора')
        else:
            admin_role.role = 'superadmin'
            admin_role.is_active = True
            admin_role.save()
            self.stdout.write('Обновлена роль суперадминистратора')

    def create_system_settings(self):
        """Создание базовых системных настроек"""
        settings_data = {
            'site_name': 'HandshakeMe',
            'site_description': 'Платформа для поиска подрядчиков',
            'max_login_attempts': '5',
            'login_attempt_timeout': '600',
            'session_timeout': '1800',
            'enable_email_notifications': 'true',
            'enable_push_notifications': 'true',
            'moderation_auto_approve': 'false',
            'complaint_auto_assign': 'true',
            'max_file_upload_size': '10485760',
            'maintenance_mode': 'false',
            'registration_enabled': 'true',
        }
        
        created_count = 0
        for key, value in settings_data.items():
            setting, created = SystemSettings.objects.get_or_create(
                key=key,
                defaults={
                    'value': value,
                    'description': f'Настройка {key.replace("_", " ").title()}',
                    'is_active': True
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'Создано настроек: {created_count}')