from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    related_object_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = (
            'id', 'notification_type', 'title', 'message', 'is_read',
            'read_at', 'extra_data', 'related_object_data', 'created_at'
        )
        read_only_fields = ('created_at',)

    def get_related_object_data(self, obj):
        """Get basic information about the related object"""
        if obj.related_object:
            # Return basic info based on object type
            related_obj = obj.related_object
            data = {
                'type': obj.content_type.model,
                'id': obj.object_id
            }
            
            # Add specific fields based on object type
            if hasattr(related_obj, 'title'):
                data['title'] = related_obj.title
            elif hasattr(related_obj, 'name'):
                data['name'] = related_obj.name
            
            return data
        return None


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = (
            'email_project_updates', 'email_new_messages', 'email_applications',
            'email_reviews', 'email_marketing', 'push_project_updates',
            'push_new_messages', 'push_applications', 'push_reviews',
            'inapp_project_updates', 'inapp_new_messages', 'inapp_applications',
            'inapp_reviews', 'updated_at'
        )
        read_only_fields = ('updated_at',)


class BulkNotificationActionSerializer(serializers.Serializer):
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of notification IDs to perform action on"
    )