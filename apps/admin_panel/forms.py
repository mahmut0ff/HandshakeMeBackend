from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()


class AdminLoginForm(forms.Form):
    """Форма входа для администраторов"""
    
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'admin@handshakeme.com',
            'autocomplete': 'email'
        })
    )
    
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Введите пароль',
            'autocomplete': 'current-password'
        })
    )
    
    remember_me = forms.BooleanField(
        label='Запомнить меня',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        
        if email and password:
            # Используем наш кастомный backend для аутентификации
            self.user_cache = authenticate(
                request=self.request,
                email=email,
                password=password
            )
            
            if self.user_cache is None:
                raise ValidationError(
                    'Неверный email или пароль. Проверьте данные и попробуйте снова.',
                    code='invalid_login'
                )
            
            if not self.user_cache.is_active:
                raise ValidationError(
                    'Этот аккаунт заблокирован.',
                    code='inactive'
                )
            
            # Дополнительная проверка админских прав
            from .authentication import AdminPermissionMixin
            permission_mixin = AdminPermissionMixin()
            if not permission_mixin.has_admin_permission(self.user_cache):
                raise ValidationError(
                    'У вас нет прав доступа к админ-панели.',
                    code='no_admin_permission'
                )
        
        return self.cleaned_data
    
    def get_user(self):
        return self.user_cache


class UserSearchForm(forms.Form):
    """Форма поиска пользователей"""
    
    search = forms.CharField(
        label='Поиск',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по email, имени или ID...',
            'autocomplete': 'off'
        })
    )
    
    status = forms.ChoiceField(
        label='Статус',
        required=False,
        choices=[
            ('', 'Все статусы'),
            ('active', 'Активные'),
            ('inactive', 'Неактивные'),
            ('banned', 'Заблокированные'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    user_type = forms.ChoiceField(
        label='Тип пользователя',
        required=False,
        choices=[
            ('', 'Все типы'),
            ('client', 'Клиенты'),
            ('contractor', 'Подрядчики'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_joined = forms.ChoiceField(
        label='Дата регистрации',
        required=False,
        choices=[
            ('', 'Все время'),
            ('today', 'Сегодня'),
            ('week', 'За неделю'),
            ('month', 'За месяц'),
            ('year', 'За год'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ComplaintFilterForm(forms.Form):
    """Форма фильтрации жалоб"""
    
    status = forms.ChoiceField(
        label='Статус',
        required=False,
        choices=[
            ('', 'Все статусы'),
            ('pending', 'Ожидает рассмотрения'),
            ('in_review', 'На рассмотрении'),
            ('resolved', 'Решена'),
            ('rejected', 'Отклонена'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    complaint_type = forms.ChoiceField(
        label='Тип жалобы',
        required=False,
        choices=[
            ('', 'Все типы'),
            ('spam', 'Спам'),
            ('inappropriate', 'Неподходящий контент'),
            ('fraud', 'Мошенничество'),
            ('harassment', 'Домогательство'),
            ('fake_profile', 'Поддельный профиль'),
            ('other', 'Другое'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    assigned_to = forms.CharField(
        label='Назначено',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        label='Приоритет',
        required=False,
        choices=[
            ('', 'Все приоритеты'),
            ('high', 'Высокий'),
            ('normal', 'Обычный'),
            ('low', 'Низкий'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_range = forms.ChoiceField(
        label='Период',
        required=False,
        choices=[
            ('', 'Все время'),
            ('today', 'Сегодня'),
            ('week', 'Неделя'),
            ('month', 'Месяц'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ComplaintResolutionForm(forms.Form):
    """Форма решения жалобы"""
    
    action = forms.ChoiceField(
        label='Действие',
        choices=[
            ('resolve', 'Решить жалобу'),
            ('reject', 'Отклонить жалобу'),
            ('in_review', 'Взять в работу'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    resolution = forms.CharField(
        label='Комментарий к решению',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Опишите принятое решение и его обоснование...'
        })
    )
    
    notify_complainant = forms.BooleanField(
        label='Уведомить заявителя',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    notify_complainant = forms.BooleanField(
        label='Уведомить заявителя',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    notify_reported_user = forms.BooleanField(
        label='Уведомить пользователя, на которого подана жалоба',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class SystemMessageForm(forms.Form):
    """Форма отправки системного сообщения в чат"""
    
    message = forms.CharField(
        label='Сообщение',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Введите текст системного сообщения...'
        })
    )
    
    template = forms.ModelChoiceField(
        label='Использовать шаблон',
        required=False,
        queryset=None,
        empty_label='Без шаблона',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import MessageTemplate
        self.fields['template'].queryset = MessageTemplate.objects.filter(is_active=True)


class EmailTemplateForm(forms.ModelForm):
    """Форма создания/редактирования email шаблона"""
    
    class Meta:
        from .models import EmailTemplate
        model = EmailTemplate
        fields = ['name', 'template_type', 'subject', 'html_content', 'text_content', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'template_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'html_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'id': 'html-editor'
            }),
            'text_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


class PushNotificationForm(forms.ModelForm):
    """Форма создания push уведомления"""
    
    class Meta:
        from .models import PushNotification
        model = PushNotification
        fields = ['title', 'message', 'target_audience', 'scheduled_at', 'extra_data']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'maxlength': '500'
            }),
            'target_audience': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'extra_data': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '{"key": "value"} - JSON формат'
            })
        }
    
    def clean_extra_data(self):
        extra_data = self.cleaned_data.get('extra_data', '{}')
        if extra_data:
            try:
                import json
                json.loads(extra_data)
            except json.JSONDecodeError:
                raise ValidationError('Неверный JSON формат')
        return extra_data


class BannerForm(forms.ModelForm):
    """Форма создания/редактирования баннера"""
    
    class Meta:
        from .models import Banner
        model = Banner
        fields = [
            'title', 'description', 'image', 'link_url', 'alt_text',
            'size', 'placement', 'priority', 'start_date', 'end_date',
            'status', 'ab_test_group', 'ab_test_weight'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'link_url': forms.URLInput(attrs={'class': 'form-control'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-control'}),
            'size': forms.Select(attrs={'class': 'form-select'}),
            'placement': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'ab_test_group': forms.TextInput(attrs={'class': 'form-control'}),
            'ab_test_weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100'
            })
        }


class ModerationQueueFilterForm(forms.Form):
    """Форма фильтрации очереди модерации"""
    
    status = forms.ChoiceField(
        label='Статус',
        required=False,
        choices=[
            ('', 'Все статусы'),
            ('pending', 'Ожидает'),
            ('approved', 'Одобрено'),
            ('rejected', 'Отклонено'),
            ('needs_review', 'Требует проверки'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        label='Приоритет',
        required=False,
        choices=[
            ('', 'Все приоритеты'),
            ('urgent', 'Срочный'),
            ('high', 'Высокий'),
            ('normal', 'Обычный'),
            ('low', 'Низкий'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    content_type = forms.ChoiceField(
        label='Тип контента',
        required=False,
        choices=[
            ('', 'Все типы'),
            ('project', 'Проекты'),
            ('user', 'Пользователи'),
            ('advertisement', 'Объявления'),
            ('review', 'Отзывы'),
            ('message', 'Сообщения'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    assigned_to = forms.ModelChoiceField(
        label='Назначено',
        required=False,
        queryset=None,
        empty_label='Все модераторы',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Получаем список модераторов
        from .models import AdminRole
        moderator_users = User.objects.filter(
            admin_role__role__in=['moderator', 'admin', 'superadmin'],
            admin_role__is_active=True
        )
        self.fields['assigned_to'].queryset = moderator_users


class ModerationActionForm(forms.Form):
    """Форма действий модерации"""
    
    action = forms.ChoiceField(
        label='Действие',
        choices=[
            ('approve', 'Одобрить'),
            ('reject', 'Отклонить'),
            ('needs_review', 'Требует дополнительной проверки'),
            ('reassign', 'Переназначить'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    reason = forms.CharField(
        label='Причина/Комментарий',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Укажите причину принятого решения...'
        })
    )
    
    reassign_to = forms.ModelChoiceField(
        label='Переназначить модератору',
        required=False,
        queryset=None,
        empty_label='Выберите модератора',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    notify_author = forms.BooleanField(
        label='Уведомить автора контента',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import AdminRole
        moderator_users = User.objects.filter(
            admin_role__role__in=['moderator', 'admin', 'superadmin'],
            admin_role__is_active=True
        )
        self.fields['reassign_to'].queryset = moderator_users
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        reassign_to = cleaned_data.get('reassign_to')
        
        if action == 'reassign' and not reassign_to:
            raise ValidationError('Необходимо выбрать модератора для переназначения')
        
        return cleaned_data


class SystemSettingsForm(forms.Form):
    """Форма системных настроек"""
    
    def __init__(self, *args, **kwargs):
        settings_data = kwargs.pop('settings_data', {})
        super().__init__(*args, **kwargs)
        
        # Динамически создаем поля на основе настроек
        for key, value in settings_data.items():
            field_name = key
            
            # Определяем тип поля по значению
            if isinstance(value, bool):
                self.fields[field_name] = forms.BooleanField(
                    label=key.replace('_', ' ').title(),
                    required=False,
                    initial=value,
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                )
            elif isinstance(value, int):
                self.fields[field_name] = forms.IntegerField(
                    label=key.replace('_', ' ').title(),
                    initial=value,
                    widget=forms.NumberInput(attrs={'class': 'form-control'})
                )
            else:
                self.fields[field_name] = forms.CharField(
                    label=key.replace('_', ' ').title(),
                    initial=value,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )


class EmailCampaignForm(forms.ModelForm):
    """Форма создания/редактирования email кампании"""
    
    class Meta:
        from .models import EmailCampaign
        model = EmailCampaign
        fields = ['name', 'subject', 'template', 'target_audience', 'scheduled_at']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'template': forms.Select(attrs={'class': 'form-select'}),
            'target_audience': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import EmailTemplate
        self.fields['template'].queryset = EmailTemplate.objects.filter(is_active=True)
        self.fields['scheduled_at'].required = False
    
    def clean_scheduled_at(self):
        scheduled_at = self.cleaned_data.get('scheduled_at')
        if scheduled_at and scheduled_at <= timezone.now():
            raise ValidationError('Время отправки должно быть в будущем')
        return scheduled_at