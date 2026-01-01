from django.urls import path
from . import views

urlpatterns = [
    # Chat rooms
    path('rooms/', views.ChatRoomListCreateView.as_view(), name='chatroom_list_create'),
    path('rooms/<int:pk>/', views.ChatRoomDetailView.as_view(), name='chatroom_detail'),
    path('rooms/<int:room_id>/messages/', views.MessageListCreateView.as_view(), name='message_list_create'),
    
    # Direct messages
    path('direct/<int:user_id>/', views.DirectMessageView.as_view(), name='direct_message'),
    
    # Message management
    path('messages/<int:pk>/', views.MessageDetailView.as_view(), name='message_detail'),
    path('messages/<int:pk>/read/', views.MarkMessageReadView.as_view(), name='mark_message_read'),
    
    # File uploads
    path('upload/image/', views.ChatImageUploadView.as_view(), name='chat_image_upload'),
    path('upload/file/', views.ChatFileUploadView.as_view(), name='chat_file_upload'),
    
    # Room management
    path('rooms/<int:room_id>/participants/', views.RoomParticipantsView.as_view(), name='room_participants'),
    path('rooms/<int:room_id>/add-participant/', views.AddParticipantView.as_view(), name='add_participant'),
    path('rooms/<int:room_id>/remove-participant/', views.RemoveParticipantView.as_view(), name='remove_participant'),
    
    # Search
    path('search/', views.MessageSearchView.as_view(), name='message_search'),
    
    # Statistics
    path('stats/', views.chat_stats_view, name='chat_stats'),
]