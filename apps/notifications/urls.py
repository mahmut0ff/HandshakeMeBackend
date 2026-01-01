from django.urls import path
from . import views

urlpatterns = [
    # Notifications
    path('', views.NotificationListView.as_view(), name='notification_list'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='notification_detail'),
    path('<int:pk>/read/', views.MarkNotificationReadView.as_view(), name='mark_notification_read'),
    path('mark-all-read/', views.MarkAllNotificationsReadView.as_view(), name='mark_all_notifications_read'),
    path('unread-count/', views.UnreadNotificationCountView.as_view(), name='unread_notification_count'),
    
    # Notification preferences
    path('preferences/', views.NotificationPreferenceView.as_view(), name='notification_preferences'),
    
    # Bulk operations
    path('bulk-read/', views.BulkMarkReadView.as_view(), name='bulk_mark_read'),
    path('bulk-delete/', views.BulkDeleteView.as_view(), name='bulk_delete'),
    
    # Statistics
    path('stats/', views.notification_stats_view, name='notification_stats'),
]