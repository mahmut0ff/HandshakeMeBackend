from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.admin_panel.models import EmailTemplate

User = get_user_model()


class Command(BaseCommand):
    help = 'Создает базовые email шаблоны для уведомлений пользователей'

    def handle(self, *args, **options):
        templates = [
            {
                'name': 'Уведомление о блокировке аккаунта',
                'template_type': 'user_banned',
                'subject': 'Ваш аккаунт заблокирован - HandshakeMe',
                'html_content': '''
                <h2>Ваш аккаунт заблокирован</h2>
                <p>Уважаемый {{ user.first_name|default:user.email }},</p>
                <p>Ваш аккаунт на платформе HandshakeMe был заблокирован администратором.</p>
                {% if reason %}
                <p><strong>Причина блокировки:</strong> {{ reason }}</p>
                {% endif %}
                <p>Если вы считаете, что это ошибка, пожалуйста, свяжитесь с нашей службой поддержки.</p>
                <p>С уважением,<br>Команда HandshakeMe</p>
                ''',
                'text_content': '''
                Ваш аккаунт заблокирован
                
                Уважаемый {{ user.first_name|default:user.email }},
                
                Ваш аккаунт на платформе HandshakeMe был заблокирован администратором.
                {% if reason %}
                Причина блокировки: {{ reason }}
                {% endif %}
                
                Если вы считаете, что это ошибка, пожалуйста, свяжитесь с нашей службой поддержки.
                
                С уважением,
                Команда HandshakeMe
                '''
            },
            {
                'name': 'Уведомление о разблокировке аккаунта',
                'template_type': 'user_unbanned',
                'subject': 'Ваш аккаунт разблокирован - HandshakeMe',
                'html_content': '''
                <h2>Ваш аккаунт разблокирован</h2>
                <p>Уважаемый {{ user.first_name|default:user.email }},</p>
                <p>Ваш аккаунт на платформе HandshakeMe был разблокирован администратором.</p>
                <p>Теперь вы можете снова пользоваться всеми функциями платформы.</p>
                <p>Добро пожаловать обратно!</p>
                <p>С уважением,<br>Команда HandshakeMe</p>
                ''',
                'text_content': '''
                Ваш аккаунт разблокирован
                
                Уважаемый {{ user.first_name|default:user.email }},
                
                Ваш аккаунт на платформе HandshakeMe был разблокирован администратором.
                
                Теперь вы можете снова пользоваться всеми функциями платформы.
                
                Добро пожаловать обратно!
                
                С уважением,
                Команда HandshakeMe
                '''
            },
            {
                'name': 'Уведомление об удалении аккаунта',
                'template_type': 'user_deleted',
                'subject': 'Ваш аккаунт удален - HandshakeMe',
                'html_content': '''
                <h2>Ваш аккаунт удален</h2>
                <p>Уважаемый {{ user.first_name|default:user.email }},</p>
                <p>Ваш аккаунт на платформе HandshakeMe был удален администратором.</p>
                {% if reason %}
                <p><strong>Причина удаления:</strong> {{ reason }}</p>
                {% endif %}
                <p>Все ваши данные были удалены из системы в соответствии с нашей политикой конфиденциальности.</p>
                <p>Если у вас есть вопросы, пожалуйста, свяжитесь с нашей службой поддержки.</p>
                <p>С уважением,<br>Команда HandshakeMe</p>
                ''',
                'text_content': '''
                Ваш аккаунт удален
                
                Уважаемый {{ user.first_name|default:user.email }},
                
                Ваш аккаунт на платформе HandshakeMe был удален администратором.
                {% if reason %}
                Причина удаления: {{ reason }}
                {% endif %}
                
                Все ваши данные были удалены из системы в соответствии с нашей политикой конфиденциальности.
                
                Если у вас есть вопросы, пожалуйста, свяжитесь с нашей службой поддержки.
                
                С уважением,
                Команда HandshakeMe
                '''
            }
        ]

        created_count = 0
        for template_data in templates:
            template, created = EmailTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Создан шаблон: {template_data["name"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Шаблон уже существует: {template_data["name"]}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Создано {created_count} новых email шаблонов')
        )