from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponseForbidden
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Q, Count, Max
from django.db import models
from django.utils import timezone
from datetime import timedelta, datetime
import json
import logging

logger = logging.getLogger(__name__)

from .forms import (
    AdminLoginForm, UserSearchForm, ComplaintFilterForm, 
    ComplaintResolutionForm, SystemMessageForm, EmailTemplateForm,
    PushNotificationForm, BannerForm, SystemSettingsForm, EmailCampaignForm
)
from .models import (
    AdminRole, AdminLoginLog, AdminActionLog, SystemSettings,
    EmailTemplate, Complaint, ContentModerationQueue, PushNotification,
    Banner, SystemMessage, MessageTemplate, EmailCampaign
)
from .decorators import (
    admin_required, AdminRequiredMixin, superadmin_required,
    view_users_required, manage_users_required, moderate_content_required,
    resolve_complaints_required, manage_settings_required,
    send_notifications_required, view_analytics_required
)
from .authentication import AdminPermissionMixin
from django.contrib.auth import get_user_model

User = get_user_model()


def admin_login_view(request):
    """Страница входа в админ-панель"""
    if request.user.is_authenticated:
        # Проверяем, есть ли у пользователя админские права
        permission_mixin = AdminPermissionMixin()
        if permission_mixin.has_admin_permission(request.user):
            return redirect('admin_panel:dashboard')
        else:
            logout(request)
            messages.error(request, 'У вас нет прав доступа к админ-панели')
    
    if request.method == 'POST':
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Устанавливаем время сессии
            if form.cleaned_data.get('remember_me'):
                request.session.set_expiry(1209600)  # 2 недели
            else:
                request.session.set_expiry(0)  # До закрытия браузера
            
            messages.success(request, f'Добро пожаловать, {user.get_full_name() or user.email}!')
            
            next_url = request.GET.get('next', reverse('admin_panel:dashboard'))
            return redirect(next_url)
    else:
        form = AdminLoginForm()
    
    return render(request, 'admin_panel/login.html', {'form': form})


@admin_required()
def admin_logout_view(request):
    """Выход из админ-панели"""
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('admin_panel:login')


@method_decorator(admin_required(), name='dispatch')
class DashboardView(AdminRequiredMixin, DetailView):
    """Главная страница дашборда"""
    template_name = 'admin_panel/dashboard.html'
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Статистика пользователей
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        new_users_today = User.objects.filter(
            date_joined__date=timezone.now().date()
        ).count()
        new_users_week = User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Статистика жалоб
        pending_complaints = Complaint.objects.filter(status='pending').count()
        total_complaints = Complaint.objects.count()
        
        # Статистика модерации
        pending_moderation = ContentModerationQueue.objects.filter(status='pending').count()
        
        # Статистика активности
        recent_logins = AdminLoginLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=24),
            success=True
        ).count()
        
        context.update({
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'new_users_today': new_users_today,
                'new_users_week': new_users_week,
                'pending_complaints': pending_complaints,
                'total_complaints': total_complaints,
                'pending_moderation': pending_moderation,
                'recent_logins': recent_logins,
            },
            'recent_actions': AdminActionLog.objects.select_related('admin_user')[:10],
            'recent_complaints': Complaint.objects.select_related('complainant')[:5],
        })
        
        return context


@method_decorator(view_users_required, name='dispatch')
class UserListView(AdminRequiredMixin, ListView):
    """Список пользователей"""
    model = User
    template_name = 'admin_panel/users/list.html'
    context_object_name = 'users'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        
        # Применяем фильтры
        form = UserSearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(email__icontains=search) |
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(id__icontains=search)
                )
            
            status = form.cleaned_data.get('status')
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
            
            user_type = form.cleaned_data.get('user_type')
            if user_type:
                queryset = queryset.filter(user_type=user_type)
            
            date_joined = form.cleaned_data.get('date_joined')
            if date_joined == 'today':
                queryset = queryset.filter(date_joined__date=timezone.now().date())
            elif date_joined == 'week':
                queryset = queryset.filter(date_joined__gte=timezone.now() - timedelta(days=7))
            elif date_joined == 'month':
                queryset = queryset.filter(date_joined__gte=timezone.now() - timedelta(days=30))
            elif date_joined == 'year':
                queryset = queryset.filter(date_joined__gte=timezone.now() - timedelta(days=365))
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = UserSearchForm(self.request.GET)
        return context


@method_decorator(view_users_required, name='dispatch')
class UserDetailView(AdminRequiredMixin, DetailView):
    """Детальная страница пользователя"""
    model = User
    template_name = 'admin_panel/users/detail.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.get_object()
        
        # Статистика пользователя
        context.update({
            'complaints_filed': Complaint.objects.filter(complainant=user_obj).count(),
            'complaints_against': Complaint.objects.filter(
                content_type__model='user',
                object_id=user_obj.id
            ).count(),
            'recent_actions': AdminActionLog.objects.filter(
                content_type__model='user',
                object_id=user_obj.id
            )[:10],
        })
        
        return context


@resolve_complaints_required
def complaint_list_view(request):
    """Список жалоб с расширенной фильтрацией и статистикой"""
    complaints = Complaint.objects.select_related('complainant', 'assigned_to').order_by('-created_at')
    
    # Статистика жалоб
    stats = {
        'pending_count': Complaint.objects.filter(status='pending').count(),
        'in_review_count': Complaint.objects.filter(status='in_review').count(),
        'resolved_count': Complaint.objects.filter(status='resolved').count(),
        'avg_processing_time': 0,
    }
    
    # Расчет среднего времени обработки
    resolved_complaints = Complaint.objects.filter(
        status='resolved', 
        resolved_at__isnull=False
    ).exclude(created_at__isnull=True)
    
    if resolved_complaints.exists():
        total_time = sum([
            (complaint.resolved_at - complaint.created_at).total_seconds() / 3600
            for complaint in resolved_complaints
        ])
        stats['avg_processing_time'] = total_time / resolved_complaints.count()
    
    # Применяем фильтры
    filter_form = ComplaintFilterForm(request.GET)
    current_filters = {}
    
    if filter_form.is_valid():
        status = filter_form.cleaned_data.get('status')
        if status:
            complaints = complaints.filter(status=status)
            current_filters['status'] = status
        
        complaint_type = filter_form.cleaned_data.get('complaint_type')
        if complaint_type:
            complaints = complaints.filter(complaint_type=complaint_type)
            current_filters['complaint_type'] = complaint_type
        
        assigned_to = filter_form.cleaned_data.get('assigned_to')
        if assigned_to:
            if assigned_to == 'unassigned':
                complaints = complaints.filter(assigned_to__isnull=True)
            elif assigned_to == 'me':
                complaints = complaints.filter(assigned_to=request.user)
            else:
                try:
                    moderator_id = int(assigned_to)
                    complaints = complaints.filter(assigned_to_id=moderator_id)
                except (ValueError, TypeError):
                    pass
            current_filters['assigned_to'] = assigned_to
        
        priority = filter_form.cleaned_data.get('priority')
        if priority:
            # Фильтрация по приоритету (можно добавить поле priority в модель)
            current_filters['priority'] = priority
        
        date_range = filter_form.cleaned_data.get('date_range')
        if date_range:
            now = timezone.now()
            if date_range == 'today':
                complaints = complaints.filter(created_at__date=now.date())
            elif date_range == 'week':
                complaints = complaints.filter(created_at__gte=now - timedelta(days=7))
            elif date_range == 'month':
                complaints = complaints.filter(created_at__gte=now - timedelta(days=30))
            current_filters['date_range'] = date_range
    
    # Получаем список модераторов для фильтров и массовых действий
    moderators = User.objects.filter(
        admin_role__role__in=['moderator', 'admin', 'superadmin'],
        admin_role__is_active=True
    ).distinct()
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(complaints, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'complaints': page_obj,
        'filter_form': filter_form,
        'page_obj': page_obj,
        'stats': stats,
        'current_filters': current_filters,
        'moderators': moderators,
        'status_choices': Complaint.STATUS_CHOICES,
        'complaint_type_choices': Complaint.COMPLAINT_TYPES,
    }
    
    return render(request, 'admin_panel/complaints/list.html', context)


@resolve_complaints_required
def complaint_detail_view(request, complaint_id):
    """Детальная страница жалобы"""
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    if request.method == 'POST':
        form = ComplaintResolutionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            resolution = form.cleaned_data['resolution']
            notify_complainant = form.cleaned_data.get('notify_complainant', False)
            notify_reported_user = form.cleaned_data.get('notify_reported_user', False)
            
            # Обновляем жалобу
            if action == 'resolve':
                complaint.status = 'resolved'
            elif action == 'reject':
                complaint.status = 'rejected'
            elif action == 'in_review':
                complaint.status = 'in_review'
            
            complaint.resolution = resolution
            if complaint.status in ['resolved', 'rejected']:
                complaint.resolved_at = timezone.now()
            complaint.assigned_to = request.user
            complaint.save()
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='resolve',
                description=f'Жалоба {action}: {resolution}',
                content_object=complaint,
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            # TODO: Отправка уведомлений (если notify_complainant или notify_reported_user)
            
            messages.success(request, f'Жалоба успешно обработана')
            return redirect('admin_panel:complaints')
    else:
        form = ComplaintResolutionForm()
    
    context = {
        'complaint': complaint,
        'form': form,
    }
    
    return render(request, 'admin_panel/complaints/detail.html', context)


@resolve_complaints_required
def complaint_bulk_assign_view(request):
    """Массовое назначение жалоб"""
    if request.method == 'POST':
        complaint_ids = request.POST.getlist('complaint_ids')
        assignee_id = request.POST.get('assignee_id')
        
        if not complaint_ids:
            return JsonResponse({'success': False, 'error': 'Не выбраны жалобы'})
        
        complaints = Complaint.objects.filter(id__in=complaint_ids, status='pending')
        
        if assignee_id == 'auto':
            # Автоматическое назначение - распределяем между доступными модераторами
            moderators = User.objects.filter(
                admin_role__role__in=['moderator', 'admin', 'superadmin'],
                admin_role__is_active=True
            ).distinct()
            
            if not moderators.exists():
                return JsonResponse({'success': False, 'error': 'Нет доступных модераторов'})
            
            # Простое распределение по кругу
            for i, complaint in enumerate(complaints):
                moderator = moderators[i % moderators.count()]
                complaint.assigned_to = moderator
                complaint.status = 'in_review'
                complaint.save()
                
                # Логируем действие
                AdminActionLog.objects.create(
                    admin_user=request.user,
                    action='update',
                    description=f'Автоназначение жалобы модератору {moderator.email}',
                    content_object=complaint,
                    ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
                )
        else:
            # Назначение конкретному модератору
            try:
                assignee = User.objects.get(id=assignee_id)
                complaints.update(assigned_to=assignee, status='in_review')
                
                # Логируем действие для каждой жалобы
                for complaint in complaints:
                    AdminActionLog.objects.create(
                        admin_user=request.user,
                        action='update',
                        description=f'Назначение жалобы модератору {assignee.email}',
                        content_object=complaint,
                        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
                    )
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Модератор не найден'})
        
        return JsonResponse({
            'success': True, 
            'message': f'Назначено {complaints.count()} жалоб'
        })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})


@moderate_content_required
def moderation_queue_view(request):
    """Очередь модерации с сортировкой по приоритету и фильтрацией"""
    # Базовый queryset с сортировкой по приоритету (срочный -> высокий -> обычный -> низкий)
    priority_order = {
        'urgent': 1,
        'high': 2, 
        'normal': 3,
        'low': 4
    }
    
    queue_items = ContentModerationQueue.objects.select_related(
        'assigned_to', 'moderated_by'
    ).extra(
        select={
            'priority_order': f"""
                CASE priority
                    WHEN 'urgent' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'normal' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END
            """
        }
    ).order_by('priority_order', '-created_at')
    
    # Фильтрация по статусу
    status = request.GET.get('status')
    if status and status in dict(ContentModerationQueue.STATUS_CHOICES):
        queue_items = queue_items.filter(status=status)
    
    # Фильтрация по типу контента
    content_type = request.GET.get('content_type')
    if content_type:
        queue_items = queue_items.filter(content_type__model=content_type)
    
    # Фильтрация по назначенному модератору
    assigned_to = request.GET.get('assigned_to')
    if assigned_to:
        if assigned_to == 'unassigned':
            queue_items = queue_items.filter(assigned_to__isnull=True)
        elif assigned_to == 'me':
            queue_items = queue_items.filter(assigned_to=request.user)
        else:
            try:
                queue_items = queue_items.filter(assigned_to_id=int(assigned_to))
            except (ValueError, TypeError):
                pass
    
    # Фильтрация по приоритету
    priority = request.GET.get('priority')
    if priority and priority in dict(ContentModerationQueue.PRIORITY_LEVELS):
        queue_items = queue_items.filter(priority=priority)
    
    # Статистика для дашборда модерации
    stats = {
        'total_pending': ContentModerationQueue.objects.filter(status='pending').count(),
        'urgent_pending': ContentModerationQueue.objects.filter(status='pending', priority='urgent').count(),
        'assigned_to_me': ContentModerationQueue.objects.filter(assigned_to=request.user, status='pending').count(),
        'unassigned': ContentModerationQueue.objects.filter(assigned_to__isnull=True, status='pending').count(),
    }
    
    # Получаем доступных модераторов для назначения
    moderators = User.objects.filter(
        admin_role__role__in=['superadmin', 'admin', 'moderator'],
        admin_role__is_active=True,
        is_active=True
    ).order_by('first_name', 'last_name', 'email')
    
    # Получаем уникальные типы контента в очереди
    content_types = ContentModerationQueue.objects.values_list(
        'content_type__model', flat=True
    ).distinct()
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(queue_items, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'queue_items': page_obj,
        'page_obj': page_obj,
        'status_choices': ContentModerationQueue.STATUS_CHOICES,
        'priority_choices': ContentModerationQueue.PRIORITY_LEVELS,
        'moderators': moderators,
        'content_types': content_types,
        'stats': stats,
        'current_filters': {
            'status': status,
            'content_type': content_type,
            'assigned_to': assigned_to,
            'priority': priority,
        }
    }
    
    return render(request, 'admin_panel/moderation/queue.html', context)


@moderate_content_required
def moderation_assign_view(request, queue_id):
    """Назначение модератора на элемент очереди"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    queue_item = get_object_or_404(ContentModerationQueue, id=queue_id)
    moderator_id = request.POST.get('moderator_id')
    
    try:
        if moderator_id == 'unassign':
            # Снимаем назначение
            old_moderator = queue_item.assigned_to
            queue_item.assigned_to = None
            queue_item.assigned_at = None
            queue_item.save()
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='moderate',
                description=f'Снято назначение модератора с элемента очереди',
                content_object=queue_item,
                old_values={'assigned_to': old_moderator.id if old_moderator else None},
                new_values={'assigned_to': None},
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            return JsonResponse({
                'success': True, 
                'message': 'Назначение снято',
                'assigned_to': None
            })
        
        else:
            # Назначаем модератора
            moderator = get_object_or_404(User, id=moderator_id)
            
            # Проверяем, что пользователь имеет права модератора
            if not hasattr(moderator, 'admin_role') or moderator.admin_role.role not in ['superadmin', 'admin', 'moderator']:
                return JsonResponse({'success': False, 'message': 'Пользователь не является модератором'})
            
            old_moderator = queue_item.assigned_to
            queue_item.assigned_to = moderator
            queue_item.assigned_at = timezone.now()
            queue_item.save()
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='moderate',
                description=f'Назначен модератор {moderator.email} на элемент очереди',
                content_object=queue_item,
                old_values={'assigned_to': old_moderator.id if old_moderator else None},
                new_values={'assigned_to': moderator.id},
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'Назначен модератор: {moderator.get_full_name() or moderator.email}',
                'assigned_to': {
                    'id': moderator.id,
                    'name': moderator.get_full_name() or moderator.email
                }
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@moderate_content_required
def moderation_bulk_assign_view(request):
    """Массовое назначение модераторов"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    try:
        queue_ids = request.POST.getlist('queue_ids[]')
        moderator_id = request.POST.get('moderator_id')
        
        if not queue_ids:
            return JsonResponse({'success': False, 'message': 'Не выбраны элементы для назначения'})
        
        # Получаем элементы очереди
        queue_items = ContentModerationQueue.objects.filter(
            id__in=queue_ids,
            status='pending'
        )
        
        if moderator_id == 'auto':
            # Автоматическое назначение - распределяем равномерно между доступными модераторами
            moderators = User.objects.filter(
                admin_role__role__in=['superadmin', 'admin', 'moderator'],
                admin_role__is_active=True,
                is_active=True
            )
            
            if not moderators.exists():
                return JsonResponse({'success': False, 'message': 'Нет доступных модераторов'})
            
            # Подсчитываем текущую нагрузку модераторов
            moderator_loads = {}
            for moderator in moderators:
                load = ContentModerationQueue.objects.filter(
                    assigned_to=moderator,
                    status='pending'
                ).count()
                moderator_loads[moderator] = load
            
            # Сортируем модераторов по нагрузке (меньше нагрузка = выше приоритет)
            sorted_moderators = sorted(moderator_loads.items(), key=lambda x: x[1])
            
            updated_count = 0
            for i, queue_item in enumerate(queue_items):
                # Назначаем модератора по кругу, начиная с наименее загруженного
                moderator = sorted_moderators[i % len(sorted_moderators)][0]
                
                queue_item.assigned_to = moderator
                queue_item.assigned_at = timezone.now()
                queue_item.save()
                
                # Обновляем счетчик нагрузки
                for j, (mod, load) in enumerate(sorted_moderators):
                    if mod == moderator:
                        sorted_moderators[j] = (mod, load + 1)
                        break
                
                updated_count += 1
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='moderate',
                description=f'Автоматически назначены модераторы для {updated_count} элементов',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'Автоматически назначены модераторы для {updated_count} элементов'
            })
        
        else:
            # Назначение конкретного модератора
            moderator = get_object_or_404(User, id=moderator_id)
            
            # Проверяем права модератора
            if not hasattr(moderator, 'admin_role') or moderator.admin_role.role not in ['superadmin', 'admin', 'moderator']:
                return JsonResponse({'success': False, 'message': 'Пользователь не является модератором'})
            
            updated_count = queue_items.update(
                assigned_to=moderator,
                assigned_at=timezone.now()
            )
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='moderate',
                description=f'Назначен модератор {moderator.email} для {updated_count} элементов',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'Назначен модератор для {updated_count} элементов'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@moderate_content_required  
def moderation_detail_view(request, queue_id):
    """Детальный просмотр элемента модерации"""
    queue_item = get_object_or_404(ContentModerationQueue, id=queue_id)
    
    # Получаем связанный контент (это будет зависеть от типа контента)
    content_object = queue_item.content_object
    
    # Получаем доступных модераторов для назначения
    moderators = User.objects.filter(
        admin_role__role__in=['superadmin', 'admin', 'moderator'],
        admin_role__is_active=True,
        is_active=True
    ).order_by('first_name', 'last_name', 'email')
    
    # Получаем историю действий с этим элементом модерации
    moderation_history = AdminActionLog.objects.filter(
        content_type__model='contentmoderationqueue',
        object_id=queue_item.id
    ).select_related('admin_user').order_by('timestamp')
    
    context = {
        'queue_item': queue_item,
        'content_object': content_object,
        'moderators': moderators,
        'moderation_history': moderation_history,
    }
    
    return render(request, 'admin_panel/moderation/detail.html', context)


@moderate_content_required
def moderation_approve_view(request, queue_id):
    """Одобрение контента"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    queue_item = get_object_or_404(ContentModerationQueue, id=queue_id)
    notes = request.POST.get('notes', '')
    
    try:
        # Обновляем статус элемента очереди
        queue_item.status = 'approved'
        queue_item.moderated_by = request.user
        queue_item.moderated_at = timezone.now()
        queue_item.notes = notes
        queue_item.save()
        
        # Получаем контент и обновляем его статус (если есть поле is_approved)
        content_object = queue_item.content_object
        if hasattr(content_object, 'is_approved'):
            content_object.is_approved = True
            content_object.save()
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='approve',
            description=f'Контент одобрен. Примечания: {notes}',
            content_object=queue_item,
            old_values={'status': 'pending'},
            new_values={'status': 'approved', 'notes': notes},
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        # Отправляем уведомление автору контента
        from .utils import send_content_moderation_notification
        send_content_moderation_notification(
            content_object, 
            'approved', 
            notes, 
            request.user
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Контент одобрен',
            'redirect_url': reverse('admin_panel:moderation')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@moderate_content_required
def moderation_reject_view(request, queue_id):
    """Отклонение контента"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    queue_item = get_object_or_404(ContentModerationQueue, id=queue_id)
    reason = request.POST.get('reason', '')
    notes = request.POST.get('notes', '')
    
    if not reason:
        return JsonResponse({'success': False, 'message': 'Необходимо указать причину отклонения'})
    
    try:
        # Обновляем статус элемента очереди
        queue_item.status = 'rejected'
        queue_item.moderated_by = request.user
        queue_item.moderated_at = timezone.now()
        queue_item.reason = reason
        queue_item.notes = notes
        queue_item.save()
        
        # Получаем контент и обновляем его статус
        content_object = queue_item.content_object
        if hasattr(content_object, 'is_approved'):
            content_object.is_approved = False
            content_object.save()
        
        # Если контент имеет статус, скрываем его
        if hasattr(content_object, 'is_active'):
            content_object.is_active = False
            content_object.save()
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='reject',
            description=f'Контент отклонен. Причина: {reason}. Примечания: {notes}',
            content_object=queue_item,
            old_values={'status': 'pending'},
            new_values={'status': 'rejected', 'reason': reason, 'notes': notes},
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        # Отправляем уведомление автору контента
        from .utils import send_content_moderation_notification
        send_content_moderation_notification(
            content_object, 
            'rejected', 
            f"{reason}. {notes}", 
            request.user
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Контент отклонен',
            'redirect_url': reverse('admin_panel:moderation')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@moderate_content_required
def moderation_needs_review_view(request, queue_id):
    """Пометить контент как требующий дополнительной проверки"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    queue_item = get_object_or_404(ContentModerationQueue, id=queue_id)
    notes = request.POST.get('notes', '')
    new_moderator_id = request.POST.get('assign_to')
    
    try:
        # Обновляем статус элемента очереди
        queue_item.status = 'needs_review'
        queue_item.notes = notes
        
        # Назначаем другому модератору, если указан
        if new_moderator_id:
            new_moderator = get_object_or_404(User, id=new_moderator_id)
            if hasattr(new_moderator, 'admin_role') and new_moderator.admin_role.role in ['superadmin', 'admin', 'moderator']:
                queue_item.assigned_to = new_moderator
                queue_item.assigned_at = timezone.now()
        
        queue_item.save()
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='moderate',
            description=f'Контент помечен для дополнительной проверки. Примечания: {notes}',
            content_object=queue_item,
            old_values={'status': queue_item.status},
            new_values={'status': 'needs_review', 'notes': notes},
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Контент помечен для дополнительной проверки'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@moderate_content_required
def detect_suspicious_content_view(request):
    """Автоматическое обнаружение подозрительного контента"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    try:
        from .services import SuspiciousContentDetector
        
        detector = SuspiciousContentDetector()
        detected_count = detector.scan_and_flag_content()
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='moderate',
            description=f'Запущено автоматическое обнаружение подозрительного контента. Обнаружено: {detected_count} элементов',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Обнаружено и помечено {detected_count} подозрительных элементов контента'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})




@send_notifications_required
def email_templates_view(request):
    """Управление email шаблонами"""
    templates = EmailTemplate.objects.order_by('-created_at')
    
    # Фильтрация по типу шаблона
    template_type = request.GET.get('template_type')
    if template_type:
        templates = templates.filter(template_type=template_type)
    
    # Поиск по названию
    search = request.GET.get('search')
    if search:
        templates = templates.filter(
            Q(name__icontains=search) | Q(subject__icontains=search)
        )
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(templates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'templates': page_obj,
        'page_obj': page_obj,
        'template_types': EmailTemplate.TEMPLATE_TYPES,
        'current_filters': {
            'template_type': template_type,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/email/templates.html', context)


@send_notifications_required
def email_template_create_view(request):
    """Создание нового email шаблона"""
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='create',
                description=f'Создан email шаблон: {template.name}',
                content_object=template,
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            messages.success(request, f'Email шаблон "{template.name}" создан')
            return redirect('admin_panel:email_templates')
    else:
        form = EmailTemplateForm()
    
    context = {
        'form': form,
        'title': 'Создать email шаблон',
        'action': 'create'
    }
    
    return render(request, 'admin_panel/email/template_form.html', context)


@send_notifications_required
def email_template_edit_view(request, template_id):
    """Редактирование email шаблона"""
    template = get_object_or_404(EmailTemplate, id=template_id)
    
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, instance=template)
        if form.is_valid():
            # Сохраняем старые значения для аудита
            old_values = {
                'name': template.name,
                'subject': template.subject,
                'html_content': template.html_content,
                'is_active': template.is_active
            }
            
            template = form.save()
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='update',
                description=f'Обновлен email шаблон: {template.name}',
                content_object=template,
                old_values=old_values,
                new_values={
                    'name': template.name,
                    'subject': template.subject,
                    'html_content': template.html_content,
                    'is_active': template.is_active
                },
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            messages.success(request, f'Email шаблон "{template.name}" обновлен')
            return redirect('admin_panel:email_templates')
    else:
        form = EmailTemplateForm(instance=template)
    
    context = {
        'form': form,
        'template': template,
        'title': f'Редактировать: {template.name}',
        'action': 'edit'
    }
    
    return render(request, 'admin_panel/email/template_form.html', context)


@send_notifications_required
def email_template_delete_view(request, template_id):
    """Удаление email шаблона"""
    template = get_object_or_404(EmailTemplate, id=template_id)
    
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='delete',
            description=f'Удален email шаблон: {template_name}',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        messages.success(request, f'Email шаблон "{template_name}" удален')
        return JsonResponse({'success': True, 'message': 'Шаблон удален'})
    
    return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})


@send_notifications_required
def email_template_preview_view(request, template_id):
    """Предварительный просмотр email шаблона"""
    template = get_object_or_404(EmailTemplate, id=template_id)
    
    # Получаем тестовые данные для предварительного просмотра
    test_data = {
        'user_name': 'Иван Иванов',
        'user_email': 'ivan@example.com',
        'project_title': 'Разработка веб-сайта',
        'admin_name': request.user.get_full_name() or request.user.email,
        'site_name': 'HandshakeMe',
        'site_url': request.build_absolute_uri('/'),
        'current_date': timezone.now().strftime('%d.%m.%Y'),
        'current_time': timezone.now().strftime('%H:%M'),
    }
    
    # Заменяем переменные в HTML контенте
    html_content = template.html_content
    for key, value in test_data.items():
        html_content = html_content.replace(f'{{{{{key}}}}}', str(value))
    
    # Заменяем переменные в теме
    subject = template.subject
    for key, value in test_data.items():
        subject = subject.replace(f'{{{{{key}}}}}', str(value))
    
    context = {
        'template': template,
        'preview_html': html_content,
        'preview_subject': subject,
        'test_data': test_data
    }
    
    return render(request, 'admin_panel/email/template_preview.html', context)


@send_notifications_required
def email_template_validate_view(request):
    """AJAX валидация HTML контента шаблона"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    html_content = request.POST.get('html_content', '')
    
    try:
        from bs4 import BeautifulSoup
        import re
        
        # Проверяем HTML синтаксис
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Проверяем наличие обязательных элементов для email
        errors = []
        warnings = []
        
        # Проверяем наличие DOCTYPE (рекомендуется для email)
        if not html_content.strip().startswith('<!DOCTYPE'):
            warnings.append('Рекомендуется добавить DOCTYPE для лучшей совместимости')
        
        # Проверяем наличие title
        if not soup.find('title'):
            warnings.append('Рекомендуется добавить тег <title>')
        
        # Проверяем использование таблиц для верстки (рекомендуется для email)
        if not soup.find('table'):
            warnings.append('Для лучшей совместимости с email клиентами рекомендуется использовать табличную верстку')
        
        # Проверяем переменные шаблона
        variables = re.findall(r'\{\{(\w+)\}\}', html_content)
        valid_variables = [
            'user_name', 'user_email', 'project_title', 'admin_name', 
            'site_name', 'site_url', 'current_date', 'current_time',
            'reason', 'resolution', 'complaint_id'
        ]
        
        invalid_variables = [var for var in variables if var not in valid_variables]
        if invalid_variables:
            errors.append(f'Неизвестные переменные: {", ".join(invalid_variables)}')
        
        # Проверяем CSS стили (inline рекомендуется для email)
        if soup.find('style') or soup.find('link', {'rel': 'stylesheet'}):
            warnings.append('Для лучшей совместимости рекомендуется использовать inline стили')
        
        return JsonResponse({
            'success': True,
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'variables_found': variables
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'valid': False,
            'errors': [f'Ошибка парсинга HTML: {str(e)}'],
            'warnings': []
        })


@send_notifications_required
def push_notifications_view(request):
    """Управление push уведомлениями с расширенной функциональностью"""
    from .services import PushNotificationService, NotificationAnalyticsService
    from django.core.paginator import Paginator
    
    # Фильтрация уведомлений
    notifications = PushNotification.objects.select_related('created_by').order_by('-created_at')
    
    # Применяем фильтры
    status = request.GET.get('status')
    if status and status in dict(PushNotification.STATUS_CHOICES):
        notifications = notifications.filter(status=status)
    
    audience = request.GET.get('audience')
    if audience and audience in dict(PushNotification.AUDIENCE_CHOICES):
        notifications = notifications.filter(target_audience=audience)
    
    date_range = request.GET.get('date_range')
    if date_range:
        now = timezone.now()
        if date_range == 'today':
            notifications = notifications.filter(created_at__date=now.date())
        elif date_range == 'week':
            notifications = notifications.filter(created_at__gte=now - timedelta(days=7))
        elif date_range == 'month':
            notifications = notifications.filter(created_at__gte=now - timedelta(days=30))
    
    # Пагинация
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Статистика
    stats = {
        'total_notifications': PushNotification.objects.count(),
        'sent_today': PushNotification.objects.filter(
            status='sent',
            sent_at__date=timezone.now().date()
        ).count(),
        'scheduled_count': PushNotification.objects.filter(status='scheduled').count(),
        'failed_count': PushNotification.objects.filter(status='failed').count(),
    }
    
    if request.method == 'POST':
        form = PushNotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.created_by = request.user
            notification.save()
            
            # Планируем или отправляем уведомление
            if notification.scheduled_at and notification.scheduled_at > timezone.now():
                PushNotificationService.schedule_notification(notification)
                messages.success(request, f'Push уведомление запланировано на {notification.scheduled_at.strftime("%d.%m.%Y %H:%M")}')
            else:
                # Отправляем немедленно в фоновом режиме
                from .tasks import send_push_notification_task
                send_push_notification_task.delay(notification.id)
                messages.success(request, 'Push уведомление поставлено в очередь на отправку')
            
            return redirect('admin_panel:notifications')
    else:
        form = PushNotificationForm()
    
    context = {
        'notifications': page_obj,
        'page_obj': page_obj,
        'form': form,
        'stats': stats,
        'status_choices': PushNotification.STATUS_CHOICES,
        'audience_choices': PushNotification.AUDIENCE_CHOICES,
        'current_filters': {
            'status': status,
            'audience': audience,
            'date_range': date_range,
        }
    }
    
    return render(request, 'admin_panel/notifications/list.html', context)


@send_notifications_required
def push_notification_detail_view(request, notification_id):
    """Детальная страница push уведомления с статистикой"""
    from .services import PushNotificationService
    
    notification = get_object_or_404(PushNotification, id=notification_id)
    
    # Получаем статистику доставки
    stats = PushNotificationService.get_delivery_statistics(notification)
    
    # Получаем список получателей (для отладки)
    recipients_preview = []
    if notification.total_recipients > 0:
        recipients = PushNotificationService.get_notification_recipients(notification)[:10]
        recipients_preview = recipients
    
    context = {
        'notification': notification,
        'stats': stats,
        'recipients_preview': recipients_preview,
    }
    
    return render(request, 'admin_panel/notifications/detail.html', context)


@send_notifications_required
def push_notification_send_view(request, notification_id):
    """Отправка push уведомления"""
    from .services import PushNotificationService
    from .tasks import send_push_notification_task
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    notification = get_object_or_404(PushNotification, id=notification_id)
    
    if notification.status != 'draft':
        return JsonResponse({'success': False, 'message': 'Уведомление уже отправлено или находится в процессе отправки'})
    
    try:
        # Отправляем в фоновом режиме
        send_push_notification_task.delay(notification.id)
        
        messages.success(request, 'Уведомление поставлено в очередь на отправку')
        return JsonResponse({'success': True, 'message': 'Уведомление отправляется'})
        
    except Exception as e:
        logger.error(f'Ошибка отправки уведомления {notification_id}: {str(e)}')
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@send_notifications_required
def push_notification_preview_view(request, notification_id):
    """Предварительный просмотр уведомления для разных устройств"""
    notification = get_object_or_404(PushNotification, id=notification_id)
    
    # Получаем количество получателей
    from .services import PushNotificationService
    recipients = PushNotificationService.get_notification_recipients(notification)
    recipients_count = recipients.count()
    
    context = {
        'notification': notification,
        'recipients_count': recipients_count,
    }
    
    return render(request, 'admin_panel/notifications/preview.html', context)


@send_notifications_required
def push_notification_analytics_view(request):
    """Аналитика push уведомлений"""
    from .services import NotificationAnalyticsService
    
    # Общая аналитика
    analytics = NotificationAnalyticsService.get_notification_analytics()
    
    # Топ уведомления по открытиям
    top_notifications = PushNotification.objects.filter(
        status='sent',
        total_recipients__gt=0
    ).order_by('-open_rate')[:10]
    
    # Статистика по дням (последние 30 дней)
    from django.db.models import Count, Avg
    daily_stats = []
    for i in range(30):
        date = timezone.now().date() - timedelta(days=i)
        day_notifications = PushNotification.objects.filter(
            sent_at__date=date,
            status='sent'
        )
        
        daily_stats.append({
            'date': date,
            'count': day_notifications.count(),
            'total_recipients': sum([n.total_recipients for n in day_notifications]),
            'avg_delivery_rate': day_notifications.aggregate(
                avg_rate=Avg('delivered_count')
            )['avg_rate'] or 0
        })
    
    daily_stats.reverse()  # Сортируем по возрастанию даты
    
    context = {
        'analytics': analytics,
        'top_notifications': top_notifications,
        'daily_stats': daily_stats,
    }
    
    return render(request, 'admin_panel/notifications/analytics.html', context)


@send_notifications_required
def push_notification_templates_view(request):
    """Управление шаблонами push уведомлений"""
    from .models import PushNotificationTemplate
    
    templates = PushNotificationTemplate.objects.filter(is_active=True).order_by('category', 'name')
    
    if request.method == 'POST':
        # Создание нового шаблона
        name = request.POST.get('name')
        category = request.POST.get('category')
        title_template = request.POST.get('title_template')
        message_template = request.POST.get('message_template')
        
        if name and title_template and message_template:
            template = PushNotificationTemplate.objects.create(
                name=name,
                category=category or 'general',
                title_template=title_template,
                message_template=message_template,
                created_by=request.user
            )
            messages.success(request, f'Шаблон "{name}" создан')
        else:
            messages.error(request, 'Заполните все обязательные поля')
        
        return redirect('admin_panel:push_notification_templates')
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'admin_panel/notifications/templates.html', context)


@send_notifications_required
def push_notification_schedule_view(request):
    """Планировщик push уведомлений"""
    from .services import NotificationSchedulerService
    
    # Получаем запланированные уведомления
    scheduled_notifications = NotificationSchedulerService.get_scheduled_notifications()
    
    # Статистика планировщика
    stats = {
        'scheduled_count': scheduled_notifications.count(),
        'next_notification': scheduled_notifications.first(),
    }
    
    context = {
        'scheduled_notifications': scheduled_notifications,
        'stats': stats,
    }
    
    return render(request, 'admin_panel/notifications/schedule.html', context)


@send_notifications_required
def push_notification_test_view(request):
    """Тестовая отправка push уведомления"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    title = request.POST.get('title')
    message = request.POST.get('message')
    test_user_id = request.POST.get('test_user_id')
    
    if not all([title, message, test_user_id]):
        return JsonResponse({'success': False, 'message': 'Заполните все поля'})
    
    try:
        test_user = User.objects.get(id=test_user_id)
        
        # Создаем тестовое уведомление
        notification = PushNotification.objects.create(
            title=f"[ТЕСТ] {title}",
            message=message,
            target_audience='specific',
            created_by=request.user,
            status='draft'
        )
        
        # Отправляем тестовому пользователю
        from .services import PushNotificationService
        success = PushNotificationService._send_fcm_notification(notification, test_user)
        
        if success:
            return JsonResponse({'success': True, 'message': f'Тестовое уведомление отправлено пользователю {test_user.email}'})
        else:
            return JsonResponse({'success': False, 'message': 'Ошибка отправки тестового уведомления'})
            
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Пользователь не найден'})
    except Exception as e:
        logger.error(f'Ошибка тестовой отправки: {str(e)}')
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@send_notifications_required
def push_notification_bulk_action_view(request):
    """Массовые действия с push уведомлениями"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    notification_ids = request.POST.getlist('notification_ids[]')
    action = request.POST.get('action')
    
    if not notification_ids:
        return JsonResponse({'success': False, 'message': 'Не выбраны уведомления'})
    
    notifications = PushNotification.objects.filter(id__in=notification_ids)
    
    try:
        if action == 'delete':
            # Удаляем только черновики
            draft_notifications = notifications.filter(status='draft')
            count = draft_notifications.count()
            draft_notifications.delete()
            return JsonResponse({'success': True, 'message': f'Удалено {count} уведомлений'})
            
        elif action == 'send':
            # Отправляем черновики
            from .tasks import send_push_notification_task
            draft_notifications = notifications.filter(status='draft')
            
            for notification in draft_notifications:
                send_push_notification_task.delay(notification.id)
            
            return JsonResponse({'success': True, 'message': f'Отправляется {draft_notifications.count()} уведомлений'})
            
        else:
            return JsonResponse({'success': False, 'message': 'Неизвестное действие'})
            
    except Exception as e:
        logger.error(f'Ошибка массового действия: {str(e)}')
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@admin_required(['manage_banners'])
def banners_view(request):
    """Управление баннерами"""
    banners = Banner.objects.order_by('-created_at')
    
    if request.method == 'POST':
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            banner = form.save(commit=False)
            banner.created_by = request.user
            banner.save()
            
            messages.success(request, 'Баннер создан')
            return redirect('admin_panel:banners')
    else:
        form = BannerForm()
    
    context = {
        'banners': banners,
        'form': form,
    }
    
    return render(request, 'admin_panel/banners/list.html', context)


@superadmin_required
def system_settings_view(request):
    """Системные настройки"""
    settings_data = {}
    settings_objects = SystemSettings.objects.filter(is_active=True)
    
    for setting in settings_objects:
        try:
            # Пытаемся определить тип значения
            if setting.value.lower() in ['true', 'false']:
                settings_data[setting.key] = setting.value.lower() == 'true'
            elif setting.value.isdigit():
                settings_data[setting.key] = int(setting.value)
            else:
                settings_data[setting.key] = setting.value
        except:
            settings_data[setting.key] = setting.value
    
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, settings_data=settings_data)
        if form.is_valid():
            # Сохраняем настройки
            for key, value in form.cleaned_data.items():
                setting, created = SystemSettings.objects.get_or_create(
                    key=key,
                    defaults={'value': str(value), 'updated_by': request.user}
                )
                if not created:
                    setting.value = str(value)
                    setting.updated_by = request.user
                    setting.save()
            
            messages.success(request, 'Настройки сохранены')
            return redirect('admin_panel:settings')
    else:
        form = SystemSettingsForm(settings_data=settings_data)
    
    context = {
        'form': form,
        'settings_objects': settings_objects,
    }
    
    return render(request, 'admin_panel/settings/system.html', context)


@superadmin_required
def audit_logs_view(request):
    """Журнал аудита"""
    logs = AdminActionLog.objects.select_related('admin_user').order_by('-timestamp')
    
    # Фильтрация
    action = request.GET.get('action')
    if action:
        logs = logs.filter(action=action)
    
    admin_user = request.GET.get('admin_user')
    if admin_user:
        logs = logs.filter(admin_user_id=admin_user)
    
    date_from = request.GET.get('date_from')
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__gte=date_from)
        except ValueError:
            pass
    
    date_to = request.GET.get('date_to')
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__lte=date_to)
        except ValueError:
            pass
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
        'page_obj': page_obj,
        'action_choices': AdminActionLog.ACTION_TYPES,
        'admin_users': User.objects.filter(admin_role__isnull=False),
    }
    
    return render(request, 'admin_panel/audit/logs.html', context)


@view_analytics_required
def analytics_api_view(request):
    """API для получения данных аналитики"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Статистика по дням за последние 30 дней
    days_data = []
    for i in range(30):
        date = timezone.now().date() - timedelta(days=i)
        users_count = User.objects.filter(date_joined__date=date).count()
        complaints_count = Complaint.objects.filter(created_at__date=date).count()
        
        days_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'users': users_count,
            'complaints': complaints_count,
        })
    
    days_data.reverse()  # Сортируем по возрастанию даты
    
    # Статистика по типам пользователей
    user_types = User.objects.values('user_type').annotate(count=Count('id'))
    
    # Статистика по статусам жалоб
    complaint_statuses = Complaint.objects.values('status').annotate(count=Count('id'))
    
    data = {
        'daily_stats': days_data,
        'user_types': list(user_types),
        'complaint_statuses': list(complaint_statuses),
    }
    
    return JsonResponse(data)


@manage_users_required
def user_ban_view(request, user_id):
    """Блокировка пользователя"""
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        # Блокируем пользователя
        user_obj.is_active = False
        user_obj.save()
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='ban',
            description=f'Пользователь заблокирован. Причина: {reason}',
            content_object=user_obj,
            old_values={'is_active': True},
            new_values={'is_active': False, 'ban_reason': reason},
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        # Отправляем email уведомление
        from .utils import send_user_notification_email
        send_user_notification_email(
            user_obj, 
            'user_banned', 
            {'reason': reason, 'admin': request.user}
        )
        
        messages.success(request, f'Пользователь {user_obj.email} заблокирован')
        return JsonResponse({'success': True, 'message': 'Пользователь заблокирован'})
    
    return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})


@manage_users_required
def user_unban_view(request, user_id):
    """Разблокировка пользователя"""
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Разблокируем пользователя
        user_obj.is_active = True
        user_obj.save()
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='unban',
            description=f'Пользователь разблокирован',
            content_object=user_obj,
            old_values={'is_active': False},
            new_values={'is_active': True},
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        # Отправляем email уведомление
        from .utils import send_user_notification_email
        send_user_notification_email(
            user_obj, 
            'user_unbanned', 
            {'admin': request.user}
        )
        
        messages.success(request, f'Пользователь {user_obj.email} разблокирован')
        return JsonResponse({'success': True, 'message': 'Пользователь разблокирован'})
    
    return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})


@manage_users_required
def user_soft_delete_view(request, user_id):
    """Мягкое удаление пользователя"""
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        # Помечаем пользователя как удаленного (soft delete)
        user_obj.is_active = False
        # Добавляем префикс к email для возможности создания нового аккаунта с тем же email
        if not user_obj.email.startswith('deleted_'):
            user_obj.email = f'deleted_{user_obj.id}_{user_obj.email}'
        user_obj.save()
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='delete',
            description=f'Пользователь удален (soft delete). Причина: {reason}',
            content_object=user_obj,
            old_values={'is_active': True, 'email': user_obj.email.replace(f'deleted_{user_obj.id}_', '')},
            new_values={'is_active': False, 'email': user_obj.email, 'delete_reason': reason},
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        # Отправляем email уведомление на оригинальный email
        original_email = user_obj.email.replace(f'deleted_{user_obj.id}_', '')
        from .utils import send_user_notification_email
        send_user_notification_email(
            user_obj, 
            'user_deleted', 
            {'reason': reason, 'admin': request.user},
            override_email=original_email
        )
        
        messages.success(request, f'Пользователь {original_email} удален')
        return JsonResponse({'success': True, 'message': 'Пользователь удален'})
    
    return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})


@admin_required()
def profile_view(request):
    """Профиль администратора"""
    context = {
        'recent_actions': AdminActionLog.objects.filter(
            admin_user=request.user
        ).order_by('-timestamp')[:10],
        'login_history': AdminLoginLog.objects.filter(
            user=request.user
        ).order_by('-timestamp')[:10],
    }
    
    return render(request, 'admin_panel/profile.html', context)


# Chat Management Views

@admin_required()
def chat_list_view(request):
    """Список активных чатов с поиском и фильтрацией"""
    from apps.chat.models import ChatRoom, Message
    
    # Базовый queryset с аннотациями
    chats = ChatRoom.objects.select_related('created_by', 'project').prefetch_related('participants').annotate(
        message_count=Count('messages'),
        last_message_time=models.Max('messages__created_at')
    ).order_by('-last_message_time')
    
    # Поиск по ID чата, названию или участникам
    search = request.GET.get('search')
    if search:
        chats = chats.filter(
            Q(id__icontains=search) |
            Q(name__icontains=search) |
            Q(participants__email__icontains=search) |
            Q(participants__first_name__icontains=search) |
            Q(participants__last_name__icontains=search)
        ).distinct()
    
    # Фильтрация по типу чата
    room_type = request.GET.get('room_type')
    if room_type:
        chats = chats.filter(room_type=room_type)
    
    # Фильтрация по статусу активности
    status = request.GET.get('status')
    if status == 'active':
        chats = chats.filter(is_active=True)
    elif status == 'blocked':
        chats = chats.filter(is_active=False)
    
    # Фильтрация по дате создания
    date_range = request.GET.get('date_range')
    if date_range:
        now = timezone.now()
        if date_range == 'today':
            chats = chats.filter(created_at__date=now.date())
        elif date_range == 'week':
            chats = chats.filter(created_at__gte=now - timedelta(days=7))
        elif date_range == 'month':
            chats = chats.filter(created_at__gte=now - timedelta(days=30))
    
    # Статистика чатов
    stats = {
        'total_chats': ChatRoom.objects.count(),
        'active_chats': ChatRoom.objects.filter(is_active=True).count(),
        'blocked_chats': ChatRoom.objects.filter(is_active=False).count(),
        'direct_chats': ChatRoom.objects.filter(room_type='direct').count(),
        'project_chats': ChatRoom.objects.filter(room_type='project').count(),
        'group_chats': ChatRoom.objects.filter(room_type='group').count(),
    }
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(chats, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'chats': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'room_type_choices': ChatRoom.ROOM_TYPES,
        'current_filters': {
            'search': search,
            'room_type': room_type,
            'status': status,
            'date_range': date_range,
        }
    }
    
    return render(request, 'admin_panel/chats/list.html', context)


@admin_required()
def chat_detail_view(request, chat_id):
    """Детальный просмотр чата с историей переписки"""
    from apps.chat.models import ChatRoom, Message
    
    chat = get_object_or_404(ChatRoom, id=chat_id)
    
    # Получаем сообщения с пагинацией (последние сообщения первыми)
    messages = Message.objects.filter(room=chat).select_related('sender').order_by('-created_at')
    
    # Фильтрация сообщений по типу
    message_type = request.GET.get('message_type')
    if message_type:
        messages = messages.filter(message_type=message_type)
    
    # Поиск по содержимому сообщений
    message_search = request.GET.get('message_search')
    if message_search:
        messages = messages.filter(content__icontains=message_search)
    
    # Фильтрация по отправителю
    sender_id = request.GET.get('sender_id')
    if sender_id:
        try:
            messages = messages.filter(sender_id=int(sender_id))
        except (ValueError, TypeError):
            pass
    
    # Пагинация сообщений
    from django.core.paginator import Paginator
    paginator = Paginator(messages, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Статистика чата
    chat_stats = {
        'total_messages': messages.count(),
        'participants_count': chat.participants.count(),
        'text_messages': Message.objects.filter(room=chat, message_type='text').count(),
        'image_messages': Message.objects.filter(room=chat, message_type='image').count(),
        'file_messages': Message.objects.filter(room=chat, message_type='file').count(),
        'system_messages': Message.objects.filter(room=chat, message_type='system').count(),
    }
    
    # Получаем системные сообщения для этого чата
    system_messages = SystemMessage.objects.filter(chat_id=chat.id).select_related('admin_user').order_by('-created_at')[:10]
    
    # Получаем доступные шаблоны сообщений
    message_templates = MessageTemplate.objects.filter(is_active=True).order_by('category', 'name')
    
    context = {
        'chat': chat,
        'messages': page_obj,
        'page_obj': page_obj,
        'chat_stats': chat_stats,
        'system_messages': system_messages,
        'message_templates': message_templates,
        'message_type_choices': Message.MESSAGE_TYPES,
        'current_filters': {
            'message_type': message_type,
            'message_search': message_search,
            'sender_id': sender_id,
        }
    }
    
    return render(request, 'admin_panel/chats/detail.html', context)


@admin_required()
def chat_block_view(request, chat_id):
    """Блокировка/разблокировка чата"""
    from apps.chat.models import ChatRoom
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    chat = get_object_or_404(ChatRoom, id=chat_id)
    action = request.POST.get('action')  # 'block' или 'unblock'
    reason = request.POST.get('reason', '')
    
    try:
        if action == 'block':
            chat.is_active = False
            chat.save()
            
            # Отправляем системное сообщение в чат
            system_message = SystemMessage.objects.create(
                chat_id=chat.id,
                admin_user=request.user,
                message=f"Чат заблокирован администратором. Причина: {reason}" if reason else "Чат заблокирован администратором."
            )
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='ban',
                description=f'Чат #{chat.id} заблокирован. Причина: {reason}',
                content_object=chat,
                old_values={'is_active': True},
                new_values={'is_active': False, 'block_reason': reason},
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            message = f'Чат #{chat.id} заблокирован'
            
        elif action == 'unblock':
            chat.is_active = True
            chat.save()
            
            # Отправляем системное сообщение в чат
            system_message = SystemMessage.objects.create(
                chat_id=chat.id,
                admin_user=request.user,
                message="Чат разблокирован администратором."
            )
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='unban',
                description=f'Чат #{chat.id} разблокирован',
                content_object=chat,
                old_values={'is_active': False},
                new_values={'is_active': True},
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            message = f'Чат #{chat.id} разблокирован'
        else:
            return JsonResponse({'success': False, 'message': 'Неизвестное действие'})
        
        return JsonResponse({
            'success': True, 
            'message': message,
            'new_status': 'active' if chat.is_active else 'blocked'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@admin_required()
def chat_send_system_message_view(request, chat_id):
    """Отправка системного сообщения в чат"""
    from apps.chat.models import ChatRoom
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    chat = get_object_or_404(ChatRoom, id=chat_id)
    message_content = request.POST.get('message', '').strip()
    template_id = request.POST.get('template_id')
    
    if not message_content and not template_id:
        return JsonResponse({'success': False, 'message': 'Необходимо указать сообщение или выбрать шаблон'})
    
    try:
        # Если выбран шаблон, используем его содержимое
        template = None
        if template_id:
            template = get_object_or_404(MessageTemplate, id=template_id)
            message_content = template.content
            
            # Заменяем переменные в шаблоне
            context_data = {
                'admin_name': request.user.get_full_name() or request.user.email,
                'chat_id': chat.id,
                'current_date': timezone.now().strftime('%d.%m.%Y'),
                'current_time': timezone.now().strftime('%H:%M'),
            }
            
            for key, value in context_data.items():
                message_content = message_content.replace(f'{{{{{key}}}}}', str(value))
            
            # Увеличиваем счетчик использования шаблона
            template.increment_usage()
        
        # Создаем системное сообщение
        system_message = SystemMessage.objects.create(
            chat_id=chat.id,
            admin_user=request.user,
            message=message_content,
            template=template
        )
        
        # Также создаем обычное сообщение в чате для отображения участникам
        from apps.chat.models import Message
        chat_message = Message.objects.create(
            room=chat,
            sender=request.user,  # Отправитель - администратор
            message_type='system',
            content=f"[Сообщение от администрации]\n{message_content}"
        )
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='moderate',
            description=f'Отправлено системное сообщение в чат #{chat.id}',
            content_object=system_message,
            new_values={'message': message_content, 'template_used': template.name if template else None},
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Системное сообщение отправлено',
            'system_message': {
                'id': system_message.id,
                'content': message_content,
                'created_at': system_message.created_at.strftime('%d.%m.%Y %H:%M'),
                'admin_name': request.user.get_full_name() or request.user.email
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@admin_required()
def chat_bulk_action_view(request):
    """Массовые действия с чатами"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    from apps.chat.models import ChatRoom
    
    chat_ids = request.POST.getlist('chat_ids[]')
    action = request.POST.get('action')
    reason = request.POST.get('reason', '')
    
    if not chat_ids:
        return JsonResponse({'success': False, 'message': 'Не выбраны чаты'})
    
    try:
        chats = ChatRoom.objects.filter(id__in=chat_ids)
        updated_count = 0
        
        if action == 'block':
            for chat in chats:
                if chat.is_active:
                    chat.is_active = False
                    chat.save()
                    
                    # Отправляем системное сообщение
                    SystemMessage.objects.create(
                        chat_id=chat.id,
                        admin_user=request.user,
                        message=f"Чат заблокирован администратором. Причина: {reason}" if reason else "Чат заблокирован администратором."
                    )
                    
                    updated_count += 1
            
            # Логируем массовое действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='ban',
                description=f'Массовая блокировка {updated_count} чатов. Причина: {reason}',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            message = f'Заблокировано {updated_count} чатов'
            
        elif action == 'unblock':
            for chat in chats:
                if not chat.is_active:
                    chat.is_active = True
                    chat.save()
                    
                    # Отправляем системное сообщение
                    SystemMessage.objects.create(
                        chat_id=chat.id,
                        admin_user=request.user,
                        message="Чат разблокирован администратором."
                    )
                    
                    updated_count += 1
            
            # Логируем массовое действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='unban',
                description=f'Массовая разблокировка {updated_count} чатов',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            message = f'Разблокировано {updated_count} чатов'
            
        elif action == 'send_message':
            message_content = request.POST.get('message_content', '').strip()
            template_id = request.POST.get('template_id')
            
            if not message_content and not template_id:
                return JsonResponse({'success': False, 'message': 'Необходимо указать сообщение или выбрать шаблон'})
            
            # Если выбран шаблон, используем его содержимое
            template = None
            if template_id:
                template = get_object_or_404(MessageTemplate, id=template_id)
                message_content = template.content
                
                # Заменяем переменные в шаблоне
                context_data = {
                    'admin_name': request.user.get_full_name() or request.user.email,
                    'current_date': timezone.now().strftime('%d.%m.%Y'),
                    'current_time': timezone.now().strftime('%H:%M'),
                }
                
                for key, value in context_data.items():
                    message_content = message_content.replace(f'{{{{{key}}}}}', str(value))
                
                # Увеличиваем счетчик использования шаблона
                template.increment_usage()
            
            # Отправляем сообщение во все выбранные чаты
            for chat in chats:
                # Создаем системное сообщение
                SystemMessage.objects.create(
                    chat_id=chat.id,
                    admin_user=request.user,
                    message=message_content,
                    template=template
                )
                
                # Также создаем обычное сообщение в чате для отображения участникам
                from apps.chat.models import Message
                Message.objects.create(
                    room=chat,
                    sender=request.user,
                    message_type='system',
                    content=f"[Сообщение от администрации]\n{message_content}"
                )
                
                updated_count += 1
            
            # Логируем массовое действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='moderate',
                description=f'Массовая отправка сообщений в {updated_count} чатов',
                new_values={'message': message_content, 'template_used': template.name if template else None},
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            message = f'Сообщение отправлено в {updated_count} чатов'
            
        else:
            return JsonResponse({'success': False, 'message': 'Неизвестное действие'})
        
        return JsonResponse({
            'success': True, 
            'message': message,
            'updated_count': updated_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})
          

    


@send_notifications_required
def email_campaigns_view(request):
    """Управление email кампаниями"""
    campaigns = EmailCampaign.objects.select_related('template', 'created_by').order_by('-created_at')
    
    # Фильтрация по статусу
    status = request.GET.get('status')
    if status:
        campaigns = campaigns.filter(status=status)
    
    # Фильтрация по целевой аудитории
    target_audience = request.GET.get('target_audience')
    if target_audience:
        campaigns = campaigns.filter(target_audience=target_audience)
    
    # Поиск по названию
    search = request.GET.get('search')
    if search:
        campaigns = campaigns.filter(
            Q(name__icontains=search) | Q(subject__icontains=search)
        )
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(campaigns, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'campaigns': page_obj,
        'page_obj': page_obj,
        'status_choices': EmailCampaign.STATUS_CHOICES,
        'audience_choices': PushNotification.AUDIENCE_CHOICES,
        'current_filters': {
            'status': status,
            'target_audience': target_audience,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/email/campaigns.html', context)


@send_notifications_required
def email_campaign_create_view(request):
    """Создание новой email кампании"""
    if request.method == 'POST':
        form = EmailCampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            
            # Подсчитываем количество получателей
            if campaign.target_audience == 'all':
                campaign.total_recipients = User.objects.filter(is_active=True).count()
            elif campaign.target_audience == 'active':
                campaign.total_recipients = User.objects.filter(
                    is_active=True,
                    last_login__gte=timezone.now() - timedelta(days=30)
                ).count()
            elif campaign.target_audience == 'contractors':
                campaign.total_recipients = User.objects.filter(
                    is_active=True, user_type='contractor'
                ).count()
            elif campaign.target_audience == 'clients':
                campaign.total_recipients = User.objects.filter(
                    is_active=True, user_type='client'
                ).count()
            
            campaign.save()
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='create',
                description=f'Создана email кампания: {campaign.name}',
                content_object=campaign,
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            messages.success(request, f'Email кампания "{campaign.name}" создана')
            return redirect('admin_panel:email_campaigns')
    else:
        form = EmailCampaignForm()
    
    context = {
        'form': form,
        'title': 'Создать email кампанию',
        'action': 'create'
    }
    
    return render(request, 'admin_panel/email/campaign_form.html', context)


@send_notifications_required
def email_campaign_send_view(request, campaign_id):
    """Отправка email кампании"""
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    
    if campaign.status not in ['draft', 'scheduled']:
        return JsonResponse({'success': False, 'message': 'Кампания уже отправлена или отправляется'})
    
    if request.method == 'POST':
        send_now = request.POST.get('send_now') == 'true'
        
        try:
            if send_now:
                # Отправляем немедленно через Celery
                from .tasks import send_email_campaign
                
                campaign.status = 'sending'
                campaign.sent_at = timezone.now()
                campaign.save()
                
                # Запускаем задачу отправки
                send_email_campaign.delay(campaign.id)
                
                message = 'Кампания поставлена в очередь на отправку'
            else:
                # Планируем отправку
                campaign.status = 'scheduled'
                campaign.save()
                message = 'Кампания запланирована к отправке'
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='email_send',
                description=f'Email кампания "{campaign.name}" {"отправлена" if send_now else "запланирована"}',
                content_object=campaign,
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            return JsonResponse({'success': True, 'message': message})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})

@send_notifications_required
def email_campaign_edit_view(request, campaign_id):
    """Редактирование email кампании"""
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    
    # Нельзя редактировать отправленные кампании
    if campaign.status in ['sending', 'sent']:
        messages.error(request, 'Нельзя редактировать отправленную кампанию')
        return redirect('admin_panel:email_campaigns')
    
    if request.method == 'POST':
        form = EmailCampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            # Сохраняем старые значения для аудита
            old_values = {
                'name': campaign.name,
                'subject': campaign.subject,
                'target_audience': campaign.target_audience,
                'scheduled_at': campaign.scheduled_at
            }
            
            campaign = form.save()
            
            # Пересчитываем количество получателей
            if campaign.target_audience == 'all':
                campaign.total_recipients = User.objects.filter(is_active=True).count()
            elif campaign.target_audience == 'active':
                campaign.total_recipients = User.objects.filter(
                    is_active=True,
                    last_login__gte=timezone.now() - timedelta(days=30)
                ).count()
            elif campaign.target_audience == 'contractors':
                campaign.total_recipients = User.objects.filter(
                    is_active=True, user_type='contractor'
                ).count()
            elif campaign.target_audience == 'clients':
                campaign.total_recipients = User.objects.filter(
                    is_active=True, user_type='client'
                ).count()
            
            campaign.save()
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='update',
                description=f'Обновлена email кампания: {campaign.name}',
                content_object=campaign,
                old_values=old_values,
                new_values={
                    'name': campaign.name,
                    'subject': campaign.subject,
                    'target_audience': campaign.target_audience,
                    'scheduled_at': campaign.scheduled_at
                },
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            messages.success(request, f'Email кампания "{campaign.name}" обновлена')
            return redirect('admin_panel:email_campaigns')
    else:
        form = EmailCampaignForm(instance=campaign)
    
    context = {
        'form': form,
        'campaign': campaign,
        'title': f'Редактировать: {campaign.name}',
        'action': 'edit'
    }
    
    return render(request, 'admin_panel/email/campaign_form.html', context)


@send_notifications_required
def email_campaign_delete_view(request, campaign_id):
    """Удаление email кампании"""
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    
    # Нельзя удалять отправляющиеся кампании
    if campaign.status == 'sending':
        return JsonResponse({'success': False, 'message': 'Нельзя удалить отправляющуюся кампанию'})
    
    if request.method == 'POST':
        campaign_name = campaign.name
        campaign.delete()
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='delete',
            description=f'Удалена email кампания: {campaign_name}',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        return JsonResponse({'success': True, 'message': 'Кампания удалена'})
    
    return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})


@send_notifications_required
def email_campaign_preview_view(request, campaign_id):
    """Предварительный просмотр email кампании"""
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    
    # Получаем тестовые данные для предварительного просмотра
    test_data = {
        'user_name': 'Иван Иванов',
        'user_email': 'ivan@example.com',
        'project_title': 'Разработка веб-сайта',
        'admin_name': request.user.get_full_name() or request.user.email,
        'site_name': 'HandshakeMe',
        'site_url': request.build_absolute_uri('/'),
        'current_date': timezone.now().strftime('%d.%m.%Y'),
        'current_time': timezone.now().strftime('%H:%M'),
    }
    
    # Заменяем переменные в HTML контенте шаблона
    html_content = campaign.template.html_content
    for key, value in test_data.items():
        html_content = html_content.replace(f'{{{{{key}}}}}', str(value))
    
    # Заменяем переменные в теме
    subject = campaign.subject
    for key, value in test_data.items():
        subject = subject.replace(f'{{{{{key}}}}}', str(value))
    
    context = {
        'campaign': campaign,
        'preview_html': html_content,
        'preview_subject': subject,
        'test_data': test_data
    }
    
    return render(request, 'admin_panel/email/campaign_preview.html', context)


@send_notifications_required
def email_campaign_statistics_view(request, campaign_id):
    """Статистика email кампании"""
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    
    # Подготавливаем данные для графиков
    stats_data = {
        'delivery_rate': campaign.delivery_rate,
        'open_rate': campaign.open_rate,
        'click_rate': campaign.click_rate,
        'bounce_rate': campaign.bounce_rate,
        'total_recipients': campaign.total_recipients,
        'delivered_count': campaign.delivered_count,
        'opened_count': campaign.opened_count,
        'clicked_count': campaign.clicked_count,
        'bounced_count': campaign.bounced_count,
    }
    
    context = {
        'campaign': campaign,
        'stats_data': stats_data,
    }
    
    return render(request, 'admin_panel/email/campaign_statistics.html', context)


@send_notifications_required
def email_audience_preview_view(request):
    """Предварительный просмотр целевой аудитории"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    target_audience = request.POST.get('target_audience')
    
    try:
        # Получаем количество получателей для выбранной аудитории
        if target_audience == 'all':
            recipients = User.objects.filter(is_active=True)
        elif target_audience == 'active':
            recipients = User.objects.filter(
                is_active=True,
                last_login__gte=timezone.now() - timedelta(days=30)
            )
        elif target_audience == 'contractors':
            recipients = User.objects.filter(is_active=True, user_type='contractor')
        elif target_audience == 'clients':
            recipients = User.objects.filter(is_active=True, user_type='client')
        else:
            recipients = User.objects.none()
        
        count = recipients.count()
        
        # Получаем примеры получателей (первые 10)
        sample_recipients = list(recipients[:10].values('email', 'first_name', 'last_name'))
        
        return JsonResponse({
            'success': True,
            'count': count,
            'sample_recipients': sample_recipients
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})


@send_notifications_required
def email_send_test_view(request):
    """Отправка тестового email"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    template_id = request.POST.get('template_id')
    test_email = request.POST.get('test_email')
    
    if not template_id or not test_email:
        return JsonResponse({'success': False, 'message': 'Не указан шаблон или email'})
    
    try:
        template = get_object_or_404(EmailTemplate, id=template_id)
        
        # Подготавливаем тестовые данные
        test_data = {
            'user_name': 'Тестовый Пользователь',
            'user_email': test_email,
            'project_title': 'Тестовый проект',
            'admin_name': request.user.get_full_name() or request.user.email,
            'site_name': 'HandshakeMe',
            'site_url': request.build_absolute_uri('/'),
            'current_date': timezone.now().strftime('%d.%m.%Y'),
            'current_time': timezone.now().strftime('%H:%M'),
        }
        
        # Отправляем email используя EmailService
        from .services import EmailService
        
        success = EmailService.send_template_email(
            template=template,
            recipient_email=test_email,
            context_data=test_data,
            admin_user=request.user
        )
        
        if not success:
            return JsonResponse({
                'success': False, 
                'message': 'Ошибка отправки email. Проверьте логи сервера для подробностей.'
            })
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='email_send',
            description=f'Отправлен тестовый email шаблона "{template.name}" на {test_email}',
            content_object=template,
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Тестовое письмо отправлено на {test_email}. Проверьте почту (включая папку спам).'
        })
        
    except Exception as e:
        logger.error(f'Ошибка в email_send_test_view: {str(e)}')
        import traceback
        logger.error(f'Traceback: {traceback.format_exc()}')
        return JsonResponse({
            'success': False, 
            'message': f'Ошибка отправки: {str(e)}'
        })


@send_notifications_required
def email_campaign_bulk_action_view(request):
    """Массовые действия с email кампаниями"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})
    
    campaign_ids = request.POST.getlist('campaign_ids')
    action = request.POST.get('action')
    
    if not campaign_ids:
        return JsonResponse({'success': False, 'message': 'Не выбраны кампании'})
    
    try:
        campaigns = EmailCampaign.objects.filter(id__in=campaign_ids)
        updated_count = 0
        
        if action == 'send':
            # Отправляем только кампании в статусе draft или scheduled
            sendable_campaigns = campaigns.filter(status__in=['draft', 'scheduled'])
            
            for campaign in sendable_campaigns:
                # Отправляем немедленно через Celery
                from .tasks import send_email_campaign
                
                campaign.status = 'sending'
                campaign.sent_at = timezone.now()
                campaign.save()
                
                # Запускаем задачу отправки
                send_email_campaign.delay(campaign.id)
                
                updated_count += 1
            
            # Логируем массовое действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='email_send',
                description=f'Массовая отправка {updated_count} email кампаний',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            message = f'Поставлено в очередь на отправку {updated_count} кампаний'
            
        elif action == 'delete':
            # Удаляем только кампании не в статусе sending
            deletable_campaigns = campaigns.exclude(status='sending')
            
            for campaign in deletable_campaigns:
                campaign_name = campaign.name
                campaign.delete()
                updated_count += 1
            
            # Логируем массовое действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='delete',
                description=f'Массовое удаление {updated_count} email кампаний',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            message = f'Удалено {updated_count} кампаний'
            
        else:
            return JsonResponse({'success': False, 'message': 'Неизвестное действие'})
        
        return JsonResponse({
            'success': True, 
            'message': message,
            'updated_count': updated_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})

# Message Template Management Views

@admin_required()
def message_templates_view(request):
    """Управление шаблонами системных сообщений"""
    templates = MessageTemplate.objects.order_by('category', 'name')
    
    # Фильтрация по категории
    category = request.GET.get('category')
    if category:
        templates = templates.filter(category=category)
    
    # Поиск по названию
    search = request.GET.get('search')
    if search:
        templates = templates.filter(
            Q(name__icontains=search) | Q(content__icontains=search)
        )
    
    # Статистика шаблонов
    stats = {
        'total_templates': MessageTemplate.objects.count(),
        'active_templates': MessageTemplate.objects.filter(is_active=True).count(),
        'most_used': MessageTemplate.objects.order_by('-usage_count').first(),
    }
    
    context = {
        'templates': templates,
        'stats': stats,
        'categories': MessageTemplate.TEMPLATE_CATEGORIES,
        'current_filters': {
            'category': category,
            'search': search,
        }
    }
    
    return render(request, 'admin_panel/chats/message_templates.html', context)


@admin_required()
def message_template_create_view(request):
    """Создание нового шаблона сообщения"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category = request.POST.get('category')
        content = request.POST.get('content', '').strip()
        available_variables = request.POST.getlist('available_variables')
        
        if not name or not category or not content:
            messages.error(request, 'Заполните все обязательные поля')
        else:
            template = MessageTemplate.objects.create(
                name=name,
                category=category,
                content=content,
                available_variables=available_variables,
                created_by=request.user
            )
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='create',
                description=f'Создан шаблон сообщения: {template.name}',
                content_object=template,
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            messages.success(request, f'Шаблон "{template.name}" создан')
            return redirect('admin_panel:message_templates')
    
    context = {
        'categories': MessageTemplate.TEMPLATE_CATEGORIES,
        'available_variables': [
            'admin_name', 'user_name', 'chat_id', 'current_date', 'current_time',
            'project_title', 'reason', 'site_name'
        ]
    }
    
    return render(request, 'admin_panel/chats/message_template_form.html', context)


@admin_required()
def message_template_edit_view(request, template_id):
    """Редактирование шаблона сообщения"""
    template = get_object_or_404(MessageTemplate, id=template_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category = request.POST.get('category')
        content = request.POST.get('content', '').strip()
        available_variables = request.POST.getlist('available_variables')
        is_active = request.POST.get('is_active') == 'on'
        
        if not name or not category or not content:
            messages.error(request, 'Заполните все обязательные поля')
        else:
            # Сохраняем старые значения для аудита
            old_values = {
                'name': template.name,
                'category': template.category,
                'content': template.content,
                'is_active': template.is_active
            }
            
            template.name = name
            template.category = category
            template.content = content
            template.available_variables = available_variables
            template.is_active = is_active
            template.save()
            
            # Логируем действие
            AdminActionLog.objects.create(
                admin_user=request.user,
                action='update',
                description=f'Обновлен шаблон сообщения: {template.name}',
                content_object=template,
                old_values=old_values,
                new_values={
                    'name': template.name,
                    'category': template.category,
                    'content': template.content,
                    'is_active': template.is_active
                },
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            messages.success(request, f'Шаблон "{template.name}" обновлен')
            return redirect('admin_panel:message_templates')
    
    context = {
        'template': template,
        'categories': MessageTemplate.TEMPLATE_CATEGORIES,
        'available_variables': [
            'admin_name', 'user_name', 'chat_id', 'current_date', 'current_time',
            'project_title', 'reason', 'site_name'
        ]
    }
    
    return render(request, 'admin_panel/chats/message_template_form.html', context)


@admin_required()
def message_template_delete_view(request, template_id):
    """Удаление шаблона сообщения"""
    template = get_object_or_404(MessageTemplate, id=template_id)
    
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        
        # Логируем действие
        AdminActionLog.objects.create(
            admin_user=request.user,
            action='delete',
            description=f'Удален шаблон сообщения: {template_name}',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
        )
        
        return JsonResponse({'success': True, 'message': 'Шаблон удален'})
    
    return JsonResponse({'success': False, 'message': 'Метод не поддерживается'})