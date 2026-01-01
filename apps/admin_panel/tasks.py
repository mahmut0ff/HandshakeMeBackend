"""
Celery задачи для админ-панели
"""
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_push_notification_task(self, notification_id):
    """Задача для отправки push уведомления в фоновом режиме"""
    from .models import PushNotification
    from .services import PushNotificationService
    
    try:
        notification = PushNotification.objects.get(id=notification_id)
        logger.info(f'Начинаем отправку push уведомления: {notification.title}')
        
        success = PushNotificationService.send_push_notification(notification)
        
        if success:
            logger.info(f'Push уведомление успешно отправлено: {notification.title}')
            return f'Уведомление "{notification.title}" отправлено успешно'
        else:
            logger.error(f'Ошибка отправки push уведомления: {notification.title}')
            raise Exception('Ошибка отправки уведомления')
            
    except PushNotification.DoesNotExist:
        logger.error(f'Push уведомление с ID {notification_id} не найдено')
        return f'Уведомление с ID {notification_id} не найдено'
        
    except Exception as exc:
        logger.error(f'Ошибка в задаче отправки push уведомления: {str(exc)}')
        
        # Повторяем попытку с экспоненциальной задержкой
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 60  # 1, 2, 4 минуты
            logger.info(f'Повторная попытка через {countdown} секунд')
            raise self.retry(exc=exc, countdown=countdown)
        else:
            # Обновляем статус уведомления на failed
            try:
                notification = PushNotification.objects.get(id=notification_id)
                notification.status = 'failed'
                notification.save()
            except:
                pass
            
            logger.error(f'Исчерпаны попытки отправки push уведомления {notification_id}')
            return f'Не удалось отправить уведомление после {self.max_retries} попыток'


@shared_task
def send_scheduled_push_notification(notification_id):
    """Задача для отправки запланированного push уведомления"""
    from .models import PushNotification
    from .services import PushNotificationService
    
    try:
        notification = PushNotification.objects.get(id=notification_id)
        
        # Проверяем, что уведомление еще запланировано
        if notification.status != 'scheduled':
            logger.warning(f'Уведомление {notification_id} больше не запланировано (статус: {notification.status})')
            return
        
        # Проверяем время отправки
        if notification.scheduled_at > timezone.now():
            logger.warning(f'Уведомление {notification_id} еще не готово к отправке')
            return
        
        logger.info(f'Отправляем запланированное уведомление: {notification.title}')
        success = PushNotificationService.send_push_notification(notification)
        
        if success:
            logger.info(f'Запланированное уведомление отправлено: {notification.title}')
        else:
            logger.error(f'Ошибка отправки запланированного уведомления: {notification.title}')
            
    except PushNotification.DoesNotExist:
        logger.error(f'Запланированное уведомление {notification_id} не найдено')
    except Exception as e:
        logger.error(f'Ошибка отправки запланированного уведомления {notification_id}: {str(e)}')


@shared_task
def process_scheduled_notifications():
    """Периодическая задача для обработки запланированных уведомлений"""
    from .services import NotificationSchedulerService
    
    try:
        sent_count = NotificationSchedulerService.process_scheduled_notifications()
        logger.info(f'Обработано запланированных уведомлений: {sent_count}')
        return sent_count
    except Exception as e:
        logger.error(f'Ошибка обработки запланированных уведомлений: {str(e)}')
        return 0


@shared_task
def cleanup_old_notifications():
    """Очистка старых уведомлений (старше 90 дней)"""
    from .models import PushNotification
    from datetime import timedelta
    
    try:
        cutoff_date = timezone.now() - timedelta(days=90)
        
        # Удаляем старые уведомления со статусом 'sent' или 'failed'
        old_notifications = PushNotification.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['sent', 'failed']
        )
        
        count = old_notifications.count()
        old_notifications.delete()
        
        logger.info(f'Удалено старых уведомлений: {count}')
        return count
        
    except Exception as e:
        logger.error(f'Ошибка очистки старых уведомлений: {str(e)}')
        return 0


@shared_task
def update_notification_statistics():
    """Обновление статистики уведомлений"""
    from .models import PushNotification
    from .services import NotificationAnalyticsService
    
    try:
        # Получаем аналитику
        analytics = NotificationAnalyticsService.get_notification_analytics()
        
        # Здесь можно сохранить статистику в кэш или отдельную таблицу
        # для быстрого доступа к дашборду
        
        logger.info('Статистика уведомлений обновлена')
        return analytics
        
    except Exception as e:
        logger.error(f'Ошибка обновления статистики уведомлений: {str(e)}')
        return None


@shared_task(bind=True, max_retries=3)
def send_bulk_push_notifications(self, notification_ids):
    """Массовая отправка push уведомлений"""
    from .models import PushNotification
    
    try:
        notifications = PushNotification.objects.filter(
            id__in=notification_ids,
            status='draft'
        )
        
        sent_count = 0
        failed_count = 0
        
        for notification in notifications:
            try:
                # Отправляем каждое уведомление в отдельной подзадаче
                send_push_notification_task.delay(notification.id)
                sent_count += 1
            except Exception as e:
                logger.error(f'Ошибка постановки в очередь уведомления {notification.id}: {str(e)}')
                failed_count += 1
        
        logger.info(f'Массовая отправка: {sent_count} поставлено в очередь, {failed_count} ошибок')
        return {'sent': sent_count, 'failed': failed_count}
        
    except Exception as exc:
        logger.error(f'Ошибка массовой отправки уведомлений: {str(exc)}')
        
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 30  # 30, 60, 120 секунд
            raise self.retry(exc=exc, countdown=countdown)
        else:
            return {'sent': 0, 'failed': len(notification_ids)}


@shared_task
def track_notification_delivery(notification_id, user_id, event_type):
    """Отслеживание событий уведомлений (открытие, клик)"""
    from .services import PushNotificationService
    
    try:
        if event_type == 'open':
            success = PushNotificationService.track_notification_open(notification_id, user_id)
        elif event_type == 'click':
            success = PushNotificationService.track_notification_click(notification_id, user_id)
        else:
            logger.warning(f'Неизвестный тип события: {event_type}')
            return False
        
        if success:
            logger.info(f'Отслежено событие {event_type} для уведомления {notification_id} от пользователя {user_id}')
        
        return success
        
    except Exception as e:
        logger.error(f'Ошибка отслеживания события {event_type}: {str(e)}')
        return False