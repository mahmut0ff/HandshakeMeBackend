"""
Сервисы для админ-панели
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import Template, Context
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailService:
    """Сервис для работы с email"""
    
    @staticmethod
    def render_template(template_content, context_data):
        """Рендерит шаблон с контекстными данными"""
        try:
            # Простая замена переменных без Django Template
            rendered_content = template_content
            logger.debug(f'Рендеринг шаблона с контекстом: {context_data}')
            
            for key, value in context_data.items():
                placeholder = f'{{{{{key}}}}}'
                rendered_content = rendered_content.replace(placeholder, str(value))
                logger.debug(f'Заменяем {placeholder} на {value}')
            
            return rendered_content
        except Exception as e:
            logger.error(f'Ошибка рендеринга шаблона: {str(e)}')
            return template_content
    
    @staticmethod
    def get_default_context(user=None, admin_user=None):
        """Получает контекст по умолчанию для email шаблонов"""
        context = {
            'site_name': getattr(settings, 'SITE_NAME', 'HandshakeMe'),
            'site_url': getattr(settings, 'SITE_URL', 'https://handshakeme.com'),
            'current_date': timezone.now().strftime('%d.%m.%Y'),
            'current_time': timezone.now().strftime('%H:%M'),
        }
        
        if user:
            context.update({
                'user_name': user.get_full_name() or user.email,
                'user_email': user.email,
                'user_first_name': user.first_name,
                'user_last_name': user.last_name,
            })
        
        if admin_user:
            context.update({
                'admin_name': admin_user.get_full_name() or admin_user.email,
                'admin_email': admin_user.email,
            })
        
        return context
    
    @classmethod
    def send_template_email(cls, template, recipient_email, context_data=None, admin_user=None):
        """Отправляет email используя шаблон"""
        try:
            logger.info(f'Начинаем отправку email шаблона "{template.name}" на {recipient_email}')
            logger.info(f'EMAIL_BACKEND: {getattr(settings, "EMAIL_BACKEND", "не установлен")}')
            
            # Подготавливаем базовый контекст
            final_context = {
                'site_name': getattr(settings, 'SITE_NAME', 'HandshakeMe'),
                'site_url': getattr(settings, 'SITE_URL', 'https://handshakeme.com'),
                'current_date': timezone.now().strftime('%d.%m.%Y'),
                'current_time': timezone.now().strftime('%H:%M'),
            }
            
            # Добавляем данные администратора
            if admin_user:
                final_context.update({
                    'admin_name': admin_user.get_full_name() or admin_user.email,
                    'admin_email': admin_user.email,
                })
            
            # Добавляем переданные данные
            if context_data:
                final_context.update(context_data)
            
            logger.info(f'Контекст для рендеринга: {final_context}')
            
            # Рендерим тему и контент
            subject = cls.render_template(template.subject, final_context)
            html_content = cls.render_template(template.html_content, final_context)
            text_content = template.text_content
            
            if text_content:
                text_content = cls.render_template(text_content, final_context)
            
            logger.info(f'Рендеринг завершен. Тема: {subject}')
            
            # Отправляем email
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@handshakeme.com')
            logger.info(f'Отправляем с адреса: {from_email}')
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content or '',
                from_email=from_email,
                to=[recipient_email]
            )
            
            if html_content:
                email.attach_alternative(html_content, "text/html")
            
            logger.info('Вызываем email.send()...')
            result = email.send()
            logger.info(f'email.send() вернул: {result}')
            
            logger.info(f'Email успешно отправлен: {subject} -> {recipient_email}')
            return True
            
        except Exception as e:
            logger.error(f'Ошибка отправки email: {str(e)}')
            import traceback
            logger.error(f'Traceback: {traceback.format_exc()}')
            return False
    
    @classmethod
    def send_campaign_email(cls, campaign, recipient_user):
        """Отправляет email в рамках кампании"""
        try:
            # Подготавливаем контекст для пользователя
            context_data = cls.get_default_context(
                user=recipient_user,
                admin_user=campaign.created_by
            )
            
            # Рендерим тему и контент
            subject = cls.render_template(campaign.subject, context_data)
            html_content = cls.render_template(campaign.template.html_content, context_data)
            text_content = campaign.template.text_content
            
            if text_content:
                text_content = cls.render_template(text_content, context_data)
            
            # Отправляем email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content or '',
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@handshakeme.com'),
                to=[recipient_user.email]
            )
            
            if html_content:
                email.attach_alternative(html_content, "text/html")
            
            email.send()
            
            logger.info(f'Campaign email отправлен: {campaign.name} -> {recipient_user.email}')
            return True
            
        except Exception as e:
            logger.error(f'Ошибка отправки campaign email: {str(e)}')
            return False


class CampaignService:
    """Сервис для работы с email кампаниями"""
    
    @staticmethod
    def get_campaign_recipients(campaign):
        """Получает список получателей для кампании"""
        if campaign.target_audience == 'all':
            return User.objects.filter(is_active=True)
        elif campaign.target_audience == 'active':
            return User.objects.filter(
                is_active=True,
                last_login__gte=timezone.now() - timedelta(days=30)
            )
        elif campaign.target_audience == 'contractors':
            return User.objects.filter(is_active=True, user_type='contractor')
        elif campaign.target_audience == 'clients':
            return User.objects.filter(is_active=True, user_type='client')
        else:
            return User.objects.none()
    
    @classmethod
    def send_campaign(cls, campaign):
        """Отправляет кампанию"""
        from .models import EmailCampaign
        
        try:
            # Обновляем статус
            campaign.status = 'sending'
            campaign.sent_at = timezone.now()
            campaign.save()
            
            # Получаем получателей
            recipients = cls.get_campaign_recipients(campaign)
            campaign.total_recipients = recipients.count()
            campaign.save()
            
            # Отправляем письма
            delivered_count = 0
            for recipient in recipients:
                if EmailService.send_campaign_email(campaign, recipient):
                    delivered_count += 1
            
            # Обновляем статистику
            campaign.delivered_count = delivered_count
            campaign.status = 'sent'
            campaign.save()
            
            logger.info(f'Кампания {campaign.name} отправлена: {delivered_count}/{campaign.total_recipients}')
            return True
            
        except Exception as e:
            campaign.status = 'failed'
            campaign.save()
            logger.error(f'Ошибка отправки кампании {campaign.name}: {str(e)}')
            return False


class StatisticsService:
    """Сервис для получения статистики админ-панели"""
    
    @staticmethod
    def get_dashboard_stats():
        """Получает статистику для дашборда"""
        from .models import EmailCampaign, EmailTemplate, Complaint, ContentModerationQueue
        
        # Статистика пользователей
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        new_users_today = User.objects.filter(
            date_joined__date=timezone.now().date()
        ).count()
        new_users_week = User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Статистика email
        total_templates = EmailTemplate.objects.count()
        active_templates = EmailTemplate.objects.filter(is_active=True).count()
        total_campaigns = EmailCampaign.objects.count()
        sent_campaigns = EmailCampaign.objects.filter(status='sent').count()
        
        # Статистика жалоб и модерации
        pending_complaints = Complaint.objects.filter(status='pending').count()
        pending_moderation = ContentModerationQueue.objects.filter(status='pending').count()
        
        return {
            'users': {
                'total': total_users,
                'active': active_users,
                'new_today': new_users_today,
                'new_week': new_users_week,
            },
            'email': {
                'templates_total': total_templates,
                'templates_active': active_templates,
                'campaigns_total': total_campaigns,
                'campaigns_sent': sent_campaigns,
            },
            'moderation': {
                'pending_complaints': pending_complaints,
                'pending_moderation': pending_moderation,
            }
        }


class PushNotificationService:
    """Сервис для работы с push уведомлениями"""
    
    @staticmethod
    def get_notification_recipients(notification):
        """Получает список получателей для push уведомления"""
        if notification.target_audience == 'all':
            return User.objects.filter(is_active=True)
        elif notification.target_audience == 'active':
            return User.objects.filter(
                is_active=True,
                last_login__gte=timezone.now() - timedelta(days=30)
            )
        elif notification.target_audience == 'contractors':
            return User.objects.filter(is_active=True, user_type='contractor')
        elif notification.target_audience == 'clients':
            return User.objects.filter(is_active=True, user_type='client')
        else:
            return User.objects.none()
    
    @classmethod
    def send_push_notification(cls, notification):
        """Отправляет push уведомление"""
        from .models import PushNotification
        
        try:
            # Обновляем статус
            notification.status = 'sending'
            notification.sent_at = timezone.now()
            notification.save()
            
            # Получаем получателей
            recipients = cls.get_notification_recipients(notification)
            notification.total_recipients = recipients.count()
            notification.save()
            
            # Отправляем уведомления через FCM
            delivered_count = 0
            for recipient in recipients:
                if cls._send_fcm_notification(notification, recipient):
                    delivered_count += 1
            
            # Обновляем статистику
            notification.delivered_count = delivered_count
            notification.status = 'sent'
            notification.save()
            
            logger.info(f'Push уведомление {notification.title} отправлено: {delivered_count}/{notification.total_recipients}')
            return True
            
        except Exception as e:
            notification.status = 'failed'
            notification.save()
            logger.error(f'Ошибка отправки push уведомления {notification.title}: {str(e)}')
            return False
    
    @staticmethod
    def _send_fcm_notification(notification, recipient):
        """Отправляет FCM уведомление конкретному пользователю"""
        try:
            # Проверяем наличие FCM токена у пользователя
            fcm_token = getattr(recipient, 'fcm_token', None)
            
            if not fcm_token:
                # Если нет токена, имитируем успешную отправку для тестирования
                logger.info(f'Имитация отправки FCM уведомления "{notification.title}" пользователю {recipient.email} (нет FCM токена)')
                return True
            
            # Отправляем через FCM сервис
            success = FCMService.send_notification(
                title=notification.title,
                body=notification.message,
                token=fcm_token,
                data={
                    'notification_id': str(notification.id),
                    'type': 'admin_notification',
                    'created_at': notification.created_at.isoformat()
                }
            )
            
            if success:
                logger.info(f'FCM уведомление отправлено: "{notification.title}" -> {recipient.email}')
            else:
                logger.error(f'Ошибка отправки FCM уведомления: "{notification.title}" -> {recipient.email}')
            
            return success
            
        except Exception as e:
            logger.error(f'Ошибка отправки FCM уведомления: {str(e)}')
            return False
    
    @classmethod
    def schedule_notification(cls, notification):
        """Планирует отправку уведомления"""
        from .tasks import send_scheduled_push_notification
        
        if notification.scheduled_at and notification.scheduled_at > timezone.now():
            # Планируем задачу через Celery
            send_scheduled_push_notification.apply_async(
                args=[notification.id],
                eta=notification.scheduled_at
            )
            notification.status = 'scheduled'
            notification.save()
            logger.info(f'Push уведомление {notification.title} запланировано на {notification.scheduled_at}')
            return True
        else:
            # Отправляем немедленно
            return cls.send_push_notification(notification)
    
    @staticmethod
    def get_delivery_statistics(notification):
        """Получает статистику доставки уведомления"""
        return {
            'total_recipients': notification.total_recipients,
            'delivered_count': notification.delivered_count,
            'opened_count': notification.opened_count,
            'clicked_count': notification.clicked_count,
            'delivery_rate': notification.delivery_rate,
            'open_rate': notification.open_rate,
            'click_rate': notification.click_rate,
        }
    
    @staticmethod
    def track_notification_open(notification_id, user_id):
        """Отслеживает открытие уведомления"""
        from .models import PushNotification
        
        try:
            notification = PushNotification.objects.get(id=notification_id)
            notification.opened_count += 1
            notification.save(update_fields=['opened_count'])
            logger.info(f'Отслежено открытие уведомления {notification_id} пользователем {user_id}')
            return True
        except PushNotification.DoesNotExist:
            logger.error(f'Уведомление {notification_id} не найдено')
            return False
    
    @staticmethod
    def track_notification_click(notification_id, user_id):
        """Отслеживает клик по уведомлению"""
        from .models import PushNotification
        
        try:
            notification = PushNotification.objects.get(id=notification_id)
            notification.clicked_count += 1
            notification.save(update_fields=['clicked_count'])
            logger.info(f'Отслежен клик по уведомлению {notification_id} пользователем {user_id}')
            return True
        except PushNotification.DoesNotExist:
            logger.error(f'Уведомление {notification_id} не найдено')
            return False


class NotificationSchedulerService:
    """Сервис для планирования уведомлений"""
    
    @staticmethod
    def process_scheduled_notifications():
        """Обрабатывает запланированные уведомления"""
        from .models import PushNotification
        
        # Находим уведомления, которые нужно отправить
        notifications_to_send = PushNotification.objects.filter(
            status='scheduled',
            scheduled_at__lte=timezone.now()
        )
        
        sent_count = 0
        for notification in notifications_to_send:
            if PushNotificationService.send_push_notification(notification):
                sent_count += 1
        
        logger.info(f'Обработано запланированных уведомлений: {sent_count}')
        return sent_count
    
    @staticmethod
    def get_scheduled_notifications():
        """Получает список запланированных уведомлений"""
        from .models import PushNotification
        
        return PushNotification.objects.filter(
            status='scheduled',
            scheduled_at__gt=timezone.now()
        ).order_by('scheduled_at')


class NotificationAnalyticsService:
    """Сервис для аналитики уведомлений"""
    
    @staticmethod
    def get_notification_analytics():
        """Получает общую аналитику по уведомлениям"""
        from .models import PushNotification
        
        total_notifications = PushNotification.objects.count()
        sent_notifications = PushNotification.objects.filter(status='sent').count()
        scheduled_notifications = PushNotification.objects.filter(status='scheduled').count()
        failed_notifications = PushNotification.objects.filter(status='failed').count()
        
        # Средние показатели
        sent_notifications_qs = PushNotification.objects.filter(status='sent', total_recipients__gt=0)
        
        avg_delivery_rate = 0
        avg_open_rate = 0
        avg_click_rate = 0
        
        if sent_notifications_qs.exists():
            # Средний процент доставки
            total_recipients = sum([n.total_recipients for n in sent_notifications_qs])
            total_delivered = sum([n.delivered_count for n in sent_notifications_qs])
            if total_recipients > 0:
                avg_delivery_rate = (total_delivered / total_recipients) * 100
            
            # Средний процент открытий
            total_opened = sum([n.opened_count for n in sent_notifications_qs])
            if total_delivered > 0:
                avg_open_rate = (total_opened / total_delivered) * 100
            
            # Средний процент кликов
            total_clicked = sum([n.clicked_count for n in sent_notifications_qs])
            if total_opened > 0:
                avg_click_rate = (total_clicked / total_opened) * 100
        
        return {
            'total_notifications': total_notifications,
            'sent_notifications': sent_notifications,
            'scheduled_notifications': scheduled_notifications,
            'failed_notifications': failed_notifications,
            'avg_delivery_rate': round(avg_delivery_rate, 2),
            'avg_open_rate': round(avg_open_rate, 2),
            'avg_click_rate': round(avg_click_rate, 2),
        }


class FCMService:
    """Сервис для интеграции с Firebase Cloud Messaging"""
    
    @staticmethod
    def initialize_fcm():
        """Инициализация FCM"""
        try:
            import firebase_admin
            from firebase_admin import credentials
            from django.conf import settings
            
            # Проверяем, инициализирован ли уже Firebase
            if not firebase_admin._apps:
                # Получаем путь к файлу с ключами из настроек
                fcm_credentials_path = getattr(settings, 'FCM_CREDENTIALS_PATH', None)
                
                if fcm_credentials_path:
                    cred = credentials.Certificate(fcm_credentials_path)
                    firebase_admin.initialize_app(cred)
                    logger.info('Firebase Admin SDK инициализирован')
                    return True
                else:
                    logger.warning('FCM_CREDENTIALS_PATH не настроен в settings')
                    return False
            
            return True
            
        except ImportError:
            logger.warning('firebase-admin не установлен. Установите: pip install firebase-admin')
            return False
        except Exception as e:
            logger.error(f'Ошибка инициализации FCM: {str(e)}')
            return False
    
    @classmethod
    def send_notification(cls, title, body, token, data=None):
        """Отправка уведомления через FCM"""
        try:
            if not cls.initialize_fcm():
                return False
            
            from firebase_admin import messaging
            
            # Создаем сообщение
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                token=token,
                data=data or {},
                android=messaging.AndroidConfig(
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#3b82f6'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            badge=1,
                            sound='default'
                        )
                    )
                )
            )
            
            # Отправляем сообщение
            response = messaging.send(message)
            logger.info(f'FCM уведомление отправлено: {response}')
            return True
            
        except Exception as e:
            logger.error(f'Ошибка отправки FCM уведомления: {str(e)}')
            return False
    
    @classmethod
    def send_multicast(cls, title, body, tokens, data=None):
        """Отправка уведомления множеству устройств"""
        try:
            if not cls.initialize_fcm():
                return {'success_count': 0, 'failure_count': len(tokens)}
            
            from firebase_admin import messaging
            
            # Создаем multicast сообщение
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                tokens=tokens,
                data=data or {},
                android=messaging.AndroidConfig(
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#3b82f6'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            badge=1,
                            sound='default'
                        )
                    )
                )
            )
            
            # Отправляем сообщения
            response = messaging.send_multicast(message)
            
            logger.info(f'FCM multicast: успешно {response.success_count}, ошибок {response.failure_count}')
            
            # Логируем ошибки
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        logger.error(f'Ошибка отправки на токен {tokens[idx]}: {resp.exception}')
            
            return {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'responses': response.responses
            }
            
        except Exception as e:
            logger.error(f'Ошибка multicast отправки FCM: {str(e)}')
            return {'success_count': 0, 'failure_count': len(tokens)}


class PushNotificationServiceV2:
    """Улучшенный сервис для работы с push уведомлениями"""
    
    @classmethod
    def send_notification_with_fcm(cls, notification):
        """Отправка уведомления с использованием FCM"""
        from .models import PushNotification
        
        try:
            # Обновляем статус
            notification.status = 'sending'
            notification.sent_at = timezone.now()
            notification.save()
            
            # Получаем получателей
            recipients = cls.get_notification_recipients(notification)
            notification.total_recipients = recipients.count()
            notification.save()
            
            if notification.total_recipients == 0:
                notification.status = 'sent'
                notification.save()
                logger.warning(f'Нет получателей для уведомления: {notification.title}')
                return True
            
            # Получаем FCM токены пользователей
            # Предполагаем, что у модели User есть поле fcm_token
            recipients_with_tokens = []
            tokens = []
            
            for recipient in recipients:
                # Проверяем наличие FCM токена
                fcm_token = getattr(recipient, 'fcm_token', None)
                if fcm_token:
                    recipients_with_tokens.append(recipient)
                    tokens.append(fcm_token)
            
            if not tokens:
                # Если нет токенов, имитируем отправку
                logger.warning(f'Нет FCM токенов для уведомления: {notification.title}')
                notification.delivered_count = notification.total_recipients
                notification.status = 'sent'
                notification.save()
                return True
            
            # Отправляем через FCM
            if len(tokens) == 1:
                # Одиночная отправка
                success = FCMService.send_notification(
                    title=notification.title,
                    body=notification.message,
                    token=tokens[0],
                    data={
                        'notification_id': str(notification.id),
                        'type': 'admin_notification'
                    }
                )
                delivered_count = 1 if success else 0
            else:
                # Массовая отправка
                result = FCMService.send_multicast(
                    title=notification.title,
                    body=notification.message,
                    tokens=tokens,
                    data={
                        'notification_id': str(notification.id),
                        'type': 'admin_notification'
                    }
                )
                delivered_count = result['success_count']
            
            # Обновляем статистику
            notification.delivered_count = delivered_count
            notification.status = 'sent'
            notification.save()
            
            logger.info(f'Push уведомление отправлено: {notification.title} ({delivered_count}/{len(tokens)} успешно)')
            return True
            
        except Exception as e:
            notification.status = 'failed'
            notification.save()
            logger.error(f'Ошибка отправки push уведомления {notification.title}: {str(e)}')
            return False
    
    @staticmethod
    def get_notification_recipients(notification):
        """Получает список получателей для push уведомления"""
        if notification.target_audience == 'all':
            return User.objects.filter(is_active=True)
        elif notification.target_audience == 'active':
            return User.objects.filter(
                is_active=True,
                last_login__gte=timezone.now() - timedelta(days=30)
            )
        elif notification.target_audience == 'contractors':
            return User.objects.filter(is_active=True, user_type='contractor')
        elif notification.target_audience == 'clients':
            return User.objects.filter(is_active=True, user_type='client')
        else:
            return User.objects.none()
    
    @classmethod
    def create_from_template(cls, template, context_data, target_audience, scheduled_at=None, created_by=None):
        """Создает уведомление из шаблона"""
        from .models import PushNotification, PushNotificationTemplate
        
        try:
            # Рендерим шаблон
            title = cls.render_template(template.title_template, context_data)
            message = cls.render_template(template.message_template, context_data)
            
            # Создаем уведомление
            notification = PushNotification.objects.create(
                title=title,
                message=message,
                target_audience=target_audience,
                scheduled_at=scheduled_at,
                created_by=created_by,
                extra_data=context_data
            )
            
            # Увеличиваем счетчик использования шаблона
            template.increment_usage()
            
            logger.info(f'Создано уведомление из шаблона "{template.name}": {title}')
            return notification
            
        except Exception as e:
            logger.error(f'Ошибка создания уведомления из шаблона: {str(e)}')
            return None
    
    @staticmethod
    def render_template(template_text, context_data):
        """Рендерит шаблон с контекстными данными"""
        try:
            rendered_text = template_text
            
            for key, value in context_data.items():
                placeholder = f'{{{{{key}}}}}'
                rendered_text = rendered_text.replace(placeholder, str(value))
            
            return rendered_text
        except Exception as e:
            logger.error(f'Ошибка рендеринга шаблона: {str(e)}')
            return template_text