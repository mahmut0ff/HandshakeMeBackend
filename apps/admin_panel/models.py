from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()


class AdminRole(models.Model):
    """Роли администраторов"""
    ROLE_CHOICES = [
        ('superadmin', 'SuperAdmin'),
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('support', 'Support'),
        ('readonly', 'ReadOnly'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_role')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_admin_roles')
    
    class Meta:
        db_table = 'admin_roles'
        verbose_name = 'Роль администратора'
        verbose_name_plural = 'Роли администраторов'
    
    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()}"


class AdminLoginLog(models.Model):
    """Логи входов администраторов"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_login_logs')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    success = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_login_logs'
        ordering = ['-timestamp']
        verbose_name = 'Лог входа администратора'
        verbose_name_plural = 'Логи входов администраторов'
    
    def __str__(self):
        status = "Успешно" if self.success else "Неудачно"
        return f"{self.user.email} - {status} - {self.timestamp}"


class AdminActionLog(models.Model):
    """Логи действий администраторов"""
    ACTION_TYPES = [
        ('create', 'Создание'),
        ('update', 'Обновление'),
        ('delete', 'Удаление'),
        ('ban', 'Блокировка'),
        ('unban', 'Разблокировка'),
        ('approve', 'Одобрение'),
        ('reject', 'Отклонение'),
        ('moderate', 'Модерация'),
        ('email_send', 'Отправка email'),
        ('settings_change', 'Изменение настроек'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_actions')
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField()
    
    # Объект, над которым выполнено действие
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Дополнительные данные
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField()
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_action_logs'
        ordering = ['-timestamp']
        verbose_name = 'Лог действия администратора'
        verbose_name_plural = 'Логи действий администраторов'
    
    def __str__(self):
        return f"{self.admin_user.email} - {self.get_action_display()} - {self.timestamp}"


class SystemSettings(models.Model):
    """Системные настройки"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'system_settings'
        verbose_name = 'Системная настройка'
        verbose_name_plural = 'Системные настройки'
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"


class EmailTemplate(models.Model):
    """Шаблоны email уведомлений"""
    TEMPLATE_TYPES = [
        ('welcome', 'Приветствие'),
        ('project_approved', 'Проект одобрен'),
        ('project_rejected', 'Проект отклонен'),
        ('user_banned', 'Пользователь заблокирован'),
        ('complaint_resolved', 'Жалоба рассмотрена'),
        ('newsletter', 'Рассылка'),
        ('system_notification', 'Системное уведомление'),
    ]
    
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPES)
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_templates'
        verbose_name = 'Шаблон email'
        verbose_name_plural = 'Шаблоны email'
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class Complaint(models.Model):
    """Жалобы пользователей"""
    COMPLAINT_TYPES = [
        ('spam', 'Спам'),
        ('inappropriate', 'Неподходящий контент'),
        ('fraud', 'Мошенничество'),
        ('harassment', 'Домогательство'),
        ('fake_profile', 'Поддельный профиль'),
        ('other', 'Другое'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает рассмотрения'),
        ('in_review', 'На рассмотрении'),
        ('resolved', 'Решена'),
        ('rejected', 'Отклонена'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complainant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='filed_complaints')
    
    # Объект жалобы
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    complaint_type = models.CharField(max_length=20, choices=COMPLAINT_TYPES)
    description = models.TextField()
    evidence = models.JSONField(default=list, blank=True)  # Ссылки на файлы доказательств
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Рассмотрение
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_complaints')
    resolution = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'complaints'
        ordering = ['-created_at']
        verbose_name = 'Жалоба'
        verbose_name_plural = 'Жалобы'
    
    def __str__(self):
        return f"Жалоба #{self.id} - {self.get_complaint_type_display()}"


class ContentModerationQueue(models.Model):
    """Очередь модерации контента"""
    PRIORITY_LEVELS = [
        ('low', 'Низкий'),
        ('normal', 'Обычный'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
        ('needs_review', 'Требует проверки'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Контент для модерации
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Модератор
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='moderation_assignments')
    assigned_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='moderated_content')
    
    # Детали модерации
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    moderated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'content_moderation_queue'
        ordering = ['-priority', '-created_at']
        verbose_name = 'Элемент очереди модерации'
        verbose_name_plural = 'Очередь модерации'
    
    def __str__(self):
        return f"Модерация #{self.id} - {self.get_status_display()}"


# Новые модели для расширенной функциональности

class PushNotification(models.Model):
    """Push уведомления"""
    AUDIENCE_CHOICES = [
        ('all', 'Все пользователи'),
        ('active', 'Активные пользователи'),
        ('contractors', 'Подрядчики'),
        ('clients', 'Клиенты'),
        ('specific', 'Конкретные пользователи'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('scheduled', 'Запланировано'),
        ('sending', 'Отправляется'),
        ('sent', 'Отправлено'),
        ('failed', 'Ошибка'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    message = models.TextField()
    target_audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES)
    
    # Планирование
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Статистика
    total_recipients = models.IntegerField(default=0)
    delivered_count = models.IntegerField(default=0)
    opened_count = models.IntegerField(default=0)
    clicked_count = models.IntegerField(default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Дополнительные данные
    extra_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'push_notifications'
        ordering = ['-created_at']
        verbose_name = 'Push уведомление'
        verbose_name_plural = 'Push уведомления'
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    def get_recipients(self):
        """Получить список получателей на основе целевой аудитории"""
        if self.target_audience == 'all':
            return User.objects.filter(is_active=True)
        elif self.target_audience == 'active':
            return User.objects.filter(
                is_active=True,
                last_login__gte=timezone.now() - timedelta(days=30)
            )
        elif self.target_audience == 'contractors':
            return User.objects.filter(is_active=True, user_type='contractor')
        elif self.target_audience == 'clients':
            return User.objects.filter(is_active=True, user_type='client')
        return User.objects.none()
    
    @property
    def delivery_rate(self):
        """Процент доставки"""
        if self.total_recipients == 0:
            return 0
        return (self.delivered_count / self.total_recipients) * 100
    
    @property
    def open_rate(self):
        """Процент открытий"""
        if self.delivered_count == 0:
            return 0
        return (self.opened_count / self.delivered_count) * 100
    
    @property
    def click_rate(self):
        """Процент кликов"""
        if self.opened_count == 0:
            return 0
        return (self.clicked_count / self.opened_count) * 100


class Banner(models.Model):
    """Рекламные баннеры"""
    BANNER_SIZES = [
        ('728x90', 'Leaderboard (728x90)'),
        ('300x250', 'Medium Rectangle (300x250)'),
        ('320x50', 'Mobile Banner (320x50)'),
        ('300x600', 'Half Page (300x600)'),
        ('970x250', 'Billboard (970x250)'),
    ]
    
    PLACEMENT_CHOICES = [
        ('home', 'Главная страница'),
        ('projects', 'Страницы проектов'),
        ('profiles', 'Профили пользователей'),
        ('search', 'Страница поиска'),
        ('dashboard', 'Дашборд пользователя'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('active', 'Активный'),
        ('paused', 'Приостановлен'),
        ('expired', 'Истек'),
        ('rejected', 'Отклонен'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Контент баннера
    image = models.ImageField(upload_to='banners/')
    link_url = models.URLField()
    alt_text = models.CharField(max_length=255, blank=True)
    
    # Настройки размещения
    size = models.CharField(max_length=10, choices=BANNER_SIZES)
    placement = models.CharField(max_length=20, choices=PLACEMENT_CHOICES)
    priority = models.IntegerField(default=1, help_text="Чем выше число, тем выше приоритет")
    
    # Расписание
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Статус и модерация
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(default=True)
    
    # Статистика
    impressions_count = models.IntegerField(default=0)
    clicks_count = models.IntegerField(default=0)
    
    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_banners')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # A/B тестирование
    ab_test_group = models.CharField(max_length=10, blank=True, help_text="A, B, C и т.д.")
    ab_test_weight = models.IntegerField(default=100, help_text="Вес для A/B тестирования (0-100)")
    
    class Meta:
        db_table = 'banners'
        ordering = ['-priority', '-created_at']
        verbose_name = 'Баннер'
        verbose_name_plural = 'Баннеры'
    
    def __str__(self):
        return f"{self.title} ({self.get_size_display()})"
    
    @property
    def ctr(self):
        """Click-through rate (CTR)"""
        if self.impressions_count == 0:
            return 0
        return (self.clicks_count / self.impressions_count) * 100
    
    @property
    def is_expired(self):
        """Проверить, истек ли баннер"""
        return timezone.now() > self.end_date
    
    @property
    def is_scheduled(self):
        """Проверить, запланирован ли баннер на будущее"""
        return timezone.now() < self.start_date
    
    def track_impression(self):
        """Отследить показ баннера"""
        self.impressions_count += 1
        self.save(update_fields=['impressions_count'])
    
    def track_click(self):
        """Отследить клик по баннеру"""
        self.clicks_count += 1
        self.save(update_fields=['clicks_count'])


class SystemMessage(models.Model):
    """Системные сообщения в чатах"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Связь с чатом (предполагаем, что есть модель Chat)
    chat_id = models.IntegerField(help_text="ID чата из приложения chat")
    
    # Администратор, отправивший сообщение
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_system_messages')
    
    # Содержимое сообщения
    message = models.TextField()
    
    # Шаблон сообщения (если использовался)
    template = models.ForeignKey('MessageTemplate', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    is_visible = models.BooleanField(default=True)
    
    # Дополнительные данные
    extra_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'system_messages'
        ordering = ['-created_at']
        verbose_name = 'Системное сообщение'
        verbose_name_plural = 'Системные сообщения'
    
    def __str__(self):
        return f"Сообщение в чат #{self.chat_id} от {self.admin_user.email}"


class MessageTemplate(models.Model):
    """Шаблоны системных сообщений"""
    TEMPLATE_CATEGORIES = [
        ('warning', 'Предупреждение'),
        ('info', 'Информация'),
        ('moderation', 'Модерация'),
        ('support', 'Поддержка'),
        ('announcement', 'Объявление'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=TEMPLATE_CATEGORIES)
    content = models.TextField()
    
    # Переменные, которые можно использовать в шаблоне
    available_variables = models.JSONField(
        default=list, 
        blank=True,
        help_text="Список доступных переменных: ['user_name', 'project_title', etc.]"
    )
    
    # Метаданные
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_message_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Статистика использования
    usage_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'message_templates'
        ordering = ['category', 'name']
        verbose_name = 'Шаблон сообщения'
        verbose_name_plural = 'Шаблоны сообщений'
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
    
    def increment_usage(self):
        """Увеличить счетчик использования"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class EmailCampaign(models.Model):
    """Email кампании"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('scheduled', 'Запланирована'),
        ('sending', 'Отправляется'),
        ('sent', 'Отправлена'),
        ('failed', 'Ошибка'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=255)
    
    # Шаблон и контент
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE)
    
    # Целевая аудитория
    target_audience = models.CharField(max_length=20, choices=PushNotification.AUDIENCE_CHOICES)
    
    # Планирование
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Статистика
    total_recipients = models.IntegerField(default=0)
    delivered_count = models.IntegerField(default=0)
    opened_count = models.IntegerField(default=0)
    clicked_count = models.IntegerField(default=0)
    bounced_count = models.IntegerField(default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_campaigns'
        ordering = ['-created_at']
        verbose_name = 'Email кампания'
        verbose_name_plural = 'Email кампании'
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
    
    @property
    def delivery_rate(self):
        """Процент доставки"""
        if self.total_recipients == 0:
            return 0
        return (self.delivered_count / self.total_recipients) * 100
    
    @property
    def open_rate(self):
        """Процент открытий"""
        if self.delivered_count == 0:
            return 0
        return (self.opened_count / self.delivered_count) * 100
    
    @property
    def click_rate(self):
        """Процент кликов"""
        if self.opened_count == 0:
            return 0
        return (self.clicked_count / self.opened_count) * 100
    
    @property
    def bounce_rate(self):
        """Процент отказов"""
        if self.total_recipients == 0:
            return 0
        return (self.bounced_count / self.total_recipients) * 100



class PushNotificationTemplate(models.Model):
    """Шаблоны push уведомлений"""
    TEMPLATE_CATEGORIES = [
        ('general', 'Общие'),
        ('marketing', 'Маркетинг'),
        ('system', 'Системные'),
        ('reminder', 'Напоминания'),
        ('announcement', 'Объявления'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=TEMPLATE_CATEGORIES, default='general')
    
    # Шаблоны с переменными
    title_template = models.CharField(max_length=100, help_text="Используйте {{variable}} для переменных")
    message_template = models.TextField(help_text="Используйте {{variable}} для переменных")
    
    # Переменные, которые можно использовать
    available_variables = models.JSONField(
        default=list,
        blank=True,
        help_text="Список доступных переменных: ['user_name', 'project_title', etc.]"
    )
    
    # Метаданные
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_push_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Статистика использования
    usage_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'push_notification_templates'
        ordering = ['category', 'name']
        verbose_name = 'Шаблон push уведомления'
        verbose_name_plural = 'Шаблоны push уведомлений'
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
    
    def increment_usage(self):
        """Увеличить счетчик использования"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])