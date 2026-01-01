import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contractor_connect.settings')
django.setup()

from apps.accounts.models import User

# Create test user
email = 'test@example.com'
password = 'testpass123'

if User.objects.filter(email=email).exists():
    print('User already exists')
    user = User.objects.get(email=email)
else:
    user = User.objects.create_user(
        email=email,
        username='testuser',
        password=password,
        first_name='Test',
        last_name='User',
        user_type='client'
    )
    print('Test user created successfully')

print(f'Email: {email}')
print(f'Password: {password}')
print(f'User type: {user.user_type}')
print(f'Is active: {user.is_active}')