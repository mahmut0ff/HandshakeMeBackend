from django.contrib import admin
from .models import ChatRoom, Message, MessageReadStatus, ChatRoomMembership


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type', 'project', 'is_active', 'created_by', 'created_at')
    list_filter = ('room_type', 'is_active', 'created_at')
    search_fields = ('name', 'project__title', 'created_by__first_name', 'created_by__last_name')
    filter_horizontal = ('participants',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'sender', 'message_type', 'content_preview', 'is_edited', 'created_at')
    list_filter = ('message_type', 'is_edited', 'created_at')
    search_fields = ('content', 'sender__first_name', 'sender__last_name', 'room__name')
    readonly_fields = ('created_at',)
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    list_display = ('message', 'user', 'read_at')
    list_filter = ('read_at',)
    search_fields = ('message__content', 'user__first_name', 'user__last_name')


@admin.register(ChatRoomMembership)
class ChatRoomMembershipAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'role', 'joined_at', 'last_seen_at', 'is_muted', 'is_pinned')
    list_filter = ('role', 'is_muted', 'is_pinned', 'joined_at')
    search_fields = ('room__name', 'user__first_name', 'user__last_name')
    readonly_fields = ('joined_at',)