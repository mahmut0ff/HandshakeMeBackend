from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Аутентификация
    path('login/', views.admin_login_view, name='login'),
    path('logout/', views.admin_logout_view, name='logout'),
    
    # Дашборд
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    
    # Пользователи
    path('users/', views.UserListView.as_view(), name='users'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:user_id>/ban/', views.user_ban_view, name='user_ban'),
    path('users/<int:user_id>/unban/', views.user_unban_view, name='user_unban'),
    path('users/<int:user_id>/delete/', views.user_soft_delete_view, name='user_delete'),
    
    # Жалобы
    path('complaints/', views.complaint_list_view, name='complaints'),
    path('complaints/<uuid:complaint_id>/', views.complaint_detail_view, name='complaint_detail'),
    path('complaints/bulk-assign/', views.complaint_bulk_assign_view, name='complaint_bulk_assign'),
    
    # Модерация
    path('moderation/', views.moderation_queue_view, name='moderation'),
    path('moderation/<uuid:queue_id>/', views.moderation_detail_view, name='moderation_detail'),
    path('moderation/<uuid:queue_id>/assign/', views.moderation_assign_view, name='moderation_assign'),
    path('moderation/<uuid:queue_id>/approve/', views.moderation_approve_view, name='moderation_approve'),
    path('moderation/<uuid:queue_id>/reject/', views.moderation_reject_view, name='moderation_reject'),
    path('moderation/<uuid:queue_id>/needs-review/', views.moderation_needs_review_view, name='moderation_needs_review'),
    path('moderation/bulk-assign/', views.moderation_bulk_assign_view, name='moderation_bulk_assign'),
    path('moderation/detect-suspicious/', views.detect_suspicious_content_view, name='detect_suspicious_content'),
    
    # Email система
    path('email/', views.email_templates_view, name='email_templates'),
    path('email/templates/', views.email_templates_view, name='email_templates'),
    path('email/templates/create/', views.email_template_create_view, name='email_template_create'),
    path('email/templates/<int:template_id>/edit/', views.email_template_edit_view, name='email_template_edit'),
    path('email/templates/<int:template_id>/delete/', views.email_template_delete_view, name='email_template_delete'),
    path('email/templates/<int:template_id>/preview/', views.email_template_preview_view, name='email_template_preview'),
    path('email/templates/validate/', views.email_template_validate_view, name='email_template_validate'),
    
    # Email кампании
    path('email/campaigns/', views.email_campaigns_view, name='email_campaigns'),
    path('email/campaigns/create/', views.email_campaign_create_view, name='email_campaign_create'),
    path('email/campaigns/<uuid:campaign_id>/edit/', views.email_campaign_edit_view, name='email_campaign_edit'),
    path('email/campaigns/<uuid:campaign_id>/send/', views.email_campaign_send_view, name='email_campaign_send'),
    path('email/campaigns/<uuid:campaign_id>/delete/', views.email_campaign_delete_view, name='email_campaign_delete'),
    path('email/campaigns/<uuid:campaign_id>/preview/', views.email_campaign_preview_view, name='email_campaign_preview'),
    path('email/campaigns/<uuid:campaign_id>/statistics/', views.email_campaign_statistics_view, name='email_campaign_statistics'),
    path('email/campaigns/bulk-action/', views.email_campaign_bulk_action_view, name='email_campaign_bulk_action'),
    
    # Email утилиты
    path('email/audience-preview/', views.email_audience_preview_view, name='email_audience_preview'),
    path('email/send-test/', views.email_send_test_view, name='email_send_test'),
    
    # Push уведомления
    path('notifications/', views.push_notifications_view, name='notifications'),
    path('notifications/<uuid:notification_id>/', views.push_notification_detail_view, name='push_notification_detail'),
    path('notifications/<uuid:notification_id>/send/', views.push_notification_send_view, name='push_notification_send'),
    path('notifications/<uuid:notification_id>/preview/', views.push_notification_preview_view, name='push_notification_preview'),
    path('notifications/analytics/', views.push_notification_analytics_view, name='push_notification_analytics'),
    path('notifications/templates/', views.push_notification_templates_view, name='push_notification_templates'),
    path('notifications/schedule/', views.push_notification_schedule_view, name='push_notification_schedule'),
    path('notifications/test/', views.push_notification_test_view, name='push_notification_test'),
    path('notifications/bulk-action/', views.push_notification_bulk_action_view, name='push_notification_bulk_action'),
    
    # Баннеры
    path('banners/', views.banners_view, name='banners'),
    
    # Чаты
    path('chats/', views.chat_list_view, name='chats'),
    path('chats/<int:chat_id>/', views.chat_detail_view, name='chat_detail'),
    path('chats/<int:chat_id>/block/', views.chat_block_view, name='chat_block'),
    path('chats/<int:chat_id>/send-message/', views.chat_send_system_message_view, name='chat_send_message'),
    path('chats/bulk-action/', views.chat_bulk_action_view, name='chat_bulk_action'),
    
    # Шаблоны сообщений
    path('chats/templates/', views.message_templates_view, name='message_templates'),
    path('chats/templates/create/', views.message_template_create_view, name='message_template_create'),
    path('chats/templates/<uuid:template_id>/edit/', views.message_template_edit_view, name='message_template_edit'),
    path('chats/templates/<uuid:template_id>/delete/', views.message_template_delete_view, name='message_template_delete'),
    
    # Системные настройки
    path('settings/', views.system_settings_view, name='settings'),
    
    # Аудит логи
    path('audit/', views.audit_logs_view, name='audit_logs'),
    
    # API
    path('api/analytics/', views.analytics_api_view, name='analytics_api'),
]