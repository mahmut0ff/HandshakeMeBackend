# Generated migration for PushNotificationTemplate model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('admin_panel', '0003_contentmoderationqueue_assigned_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='PushNotificationTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('category', models.CharField(choices=[('general', 'Общие'), ('marketing', 'Маркетинг'), ('system', 'Системные'), ('reminder', 'Напоминания'), ('announcement', 'Объявления')], default='general', max_length=20)),
                ('title_template', models.CharField(help_text='Используйте {{variable}} для переменных', max_length=100)),
                ('message_template', models.TextField(help_text='Используйте {{variable}} для переменных')),
                ('available_variables', models.JSONField(blank=True, default=list, help_text='Список доступных переменных: [\'user_name\', \'project_title\', etc.]')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('usage_count', models.IntegerField(default=0)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_push_templates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Шаблон push уведомления',
                'verbose_name_plural': 'Шаблоны push уведомлений',
                'db_table': 'push_notification_templates',
                'ordering': ['category', 'name'],
            },
        ),
    ]