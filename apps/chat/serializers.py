from rest_framework import serializers
from apps.accounts.serializers import UserProfileSerializer
from .models import ChatRoom, Message, MessageReadStatus, ChatRoomMembership


class MessageSerializer(serializers.ModelSerializer):
    sender = UserProfileSerializer(read_only=True)
    reply_to = serializers.SerializerMethodField()
    read_by_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = (
            'id', 'sender', 'message_type', 'content', 'file', 'image',
            'is_edited', 'edited_at', 'reply_to', 'read_by_count', 'created_at'
        )
        read_only_fields = ('sender', 'is_edited', 'edited_at', 'created_at')

    def get_reply_to(self, obj):
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'content': obj.reply_to.content[:100],
                'sender_name': obj.reply_to.sender.full_name
            }
        return None

    def get_read_by_count(self, obj):
        return obj.read_status.count()


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('content', 'message_type', 'file', 'image', 'reply_to')

    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class ChatRoomMembershipSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = ChatRoomMembership
        fields = (
            'id', 'user', 'role', 'joined_at', 'last_seen_at', 
            'is_muted', 'is_pinned'
        )


class ChatRoomSerializer(serializers.ModelSerializer):
    participants = UserProfileSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = (
            'id', 'name', 'room_type', 'participants', 'project',
            'is_active', 'last_message', 'unread_count', 'participant_count',
            'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')

    def get_last_message(self, obj):
        last_message = obj.get_last_message()
        if last_message:
            return {
                'id': last_message.id,
                'content': last_message.content,
                'sender_name': last_message.sender.full_name,
                'message_type': last_message.message_type,
                'created_at': last_message.created_at
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count_for_user(request.user)
        return 0

    def get_participant_count(self, obj):
        return obj.participants.count()


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ChatRoom
        fields = ('name', 'room_type', 'participant_ids')

    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids', [])
        room = ChatRoom.objects.create(
            created_by=self.context['request'].user,
            **validated_data
        )
        
        # Add creator as participant
        room.participants.add(self.context['request'].user)
        
        # Add other participants
        if participant_ids:
            from apps.accounts.models import User
            participants = User.objects.filter(id__in=participant_ids)
            room.participants.add(*participants)
        
        return room