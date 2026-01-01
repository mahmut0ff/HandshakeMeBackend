from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.admin_panel.models import AdminRole

User = get_user_model()


class Command(BaseCommand):
    help = 'Создает администратора с правами доступа к админ-панели'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email администратора')
        parser.add_argument('--password', type=str, help='Пароль администратора')
        parser.add_argument('--role', type=str, default='superadmin', 
                          choices=['superadmin', 'admin', 'moderator', 'support', 'readonly'],
                          help='Роль администратора')

    def handle(self, *args, **options):
        email = options.get('email')
        password = options.get('password')
        role = options.get('role', 'superadmin')

        if not email:
            email = input('Введите email администратора: ')
        
        if not password:
            password = input('Введите пароль администратора: ')

        try:
            # Проверяем, существует ли пользователь
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': 'Admin',
                    'last_name': 'User',
                    'is_active': True
                }
            )

            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Создан новый пользователь: {email}')
                )
            else:
                # Обновляем пароль существующего пользователя
                user.set_password(password)
                user.is_active = True
                user.save()
                self.stdout.write(
                    self.style.WARNING(f'Обновлен существующий пользователь: {email}')
                )

            # Создаем или обновляем админскую роль
            admin_role, role_created = AdminRole.objects.get_or_create(
                user=user,
                defaults={
                    'role': role,
                    'is_active': True,
                    'created_by': user
                }
            )

            if not role_created:
                admin_role.role = role
                admin_role.is_active = True
                admin_role.save()
                self.stdout.write(
                    self.style.WARNING(f'Обновлена роль пользователя: {role}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Создана роль: {role}')
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Администратор успешно создан!\n'
                    f'Email: {email}\n'
                    f'Роль: {role}\n'
                    f'Теперь вы можете войти в админ-панель по адресу: /admin-panel/login/'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при создании администратора: {e}')
            )