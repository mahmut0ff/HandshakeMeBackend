from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model, authenticate
from apps.admin_panel.models import AdminRole

User = get_user_model()


class Command(BaseCommand):
    help = 'Проверяет данные администратора и возможность входа'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email администратора для проверки')

    def handle(self, *args, **options):
        email = options.get('email')
        
        if not email:
            email = input('Введите email администратора для проверки: ')

        try:
            # Проверяем пользователя
            user = User.objects.get(email=email)
            self.stdout.write(f'Пользователь найден: {user.email}')
            self.stdout.write(f'Активен: {user.is_active}')
            self.stdout.write(f'ID: {user.id}')
            
            # Проверяем админскую роль
            try:
                admin_role = user.admin_role
                self.stdout.write(f'Админская роль: {admin_role.role}')
                self.stdout.write(f'Роль активна: {admin_role.is_active}')
            except AttributeError:
                self.stdout.write(self.style.ERROR('У пользователя нет админской роли!'))
                return

            # Проверяем пароль
            password = input('Введите пароль для проверки: ')
            
            if user.check_password(password):
                self.stdout.write(self.style.SUCCESS('Пароль правильный!'))
                
                # Тестируем аутентификацию через наш backend
                from django.test import RequestFactory
                factory = RequestFactory()
                request = factory.post('/admin-panel/login/')
                request.META['REMOTE_ADDR'] = '127.0.0.1'
                request.META['HTTP_USER_AGENT'] = 'Test'
                
                authenticated_user = authenticate(
                    request=request,
                    email=email,
                    password=password
                )
                
                if authenticated_user:
                    self.stdout.write(self.style.SUCCESS('Аутентификация через AdminAuthenticationBackend успешна!'))
                else:
                    self.stdout.write(self.style.ERROR('Аутентификация через AdminAuthenticationBackend не удалась!'))
                    
            else:
                self.stdout.write(self.style.ERROR('Неверный пароль!'))

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Пользователь с email {email} не найден!'))
            
            # Показываем всех админов
            self.stdout.write('\nСуществующие администраторы:')
            admin_roles = AdminRole.objects.filter(is_active=True)
            for role in admin_roles:
                self.stdout.write(f'- {role.user.email} ({role.role})')