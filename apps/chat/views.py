from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.shortcuts import get_object_or_404

from .models import ChatRoom, Message, ChatRoomMembership
from .serializers import (
    ChatRoomSerializer, ChatRoomCreateSerializer, MessageSerializer,
    MessageCreateSerializer, ChatRoomMembershipSerializer
)
from .services import ChatService
from apps.accounts.models import User


class ChatRoomListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatService.get_user_chat_rooms(self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ChatRoomCreateSerializer
        return ChatRoomSerializer

    @extend_schema(
        summary="List chat rooms",
        description="Get all chat rooms for the current user"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create chat room",
        description="Create a new chat room"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ChatRoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatRoom.objects.filter(participants=self.request.user)

    @extend_schema(
        summary="Get chat room details",
        description="Retrieve specific chat room details"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DirectMessageView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get or create direct message room",
        description="Get or create a direct message room with another user"
    )
    def post(self, request, *args, **kwargs):
        other_user_id = self.kwargs['user_id']
        other_user = get_object_or_404(User, id=other_user_id)
        
        room = ChatService.get_or_create_direct_room(request.user, other_user)
        serializer = ChatRoomSerializer(room)
        return Response(serializer.data)


class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-created_at']

    def get_queryset(self):
        room_id = self.kwargs['room_id']
        room = get_object_or_404(ChatRoom, id=room_id, participants=self.request.user)
        
        before_message_id = self.request.query_params.get('before')
        limit = int(self.request.query_params.get('limit', 50))
        
        return ChatService.get_room_messages(room, self.request.user, limit, before_message_id)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MessageCreateSerializer
        return MessageSerializer

    def perform_create(self, serializer):
        room_id = self.kwargs['room_id']
        room = get_object_or_404(ChatRoom, id=room_id, participants=self.request.user)
        serializer.save(room=room, sender=self.request.user)

    @extend_schema(
        summary="List messages",
        description="Get messages for a specific chat room"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Send message",
        description="Send a message to a chat room"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(room__participants=self.request.user)

    @extend_schema(
        summary="Get message details",
        description="Retrieve specific message details"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MarkMessageReadView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Mark message as read",
        description="Mark a specific message as read"
    )
    def patch(self, request, *args, **kwargs):
        message_id = self.kwargs['pk']
        try:
            message = Message.objects.get(id=message_id, room__participants=request.user)
            from .models import MessageReadStatus
            MessageReadStatus.objects.get_or_create(message=message, user=request.user)
            return Response({"message": "Message marked as read"})
        except Message.DoesNotExist:
            return Response({"error": "Message not found"}, status=status.HTTP_404_NOT_FOUND)


class ChatImageUploadView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Upload chat image",
        description="Upload an image for chat messages"
    )
    def post(self, request, *args, **kwargs):
        # This would handle image upload for chat
        # Implementation depends on your file handling strategy
        return Response({"message": "Image upload endpoint"})


class ChatFileUploadView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Upload chat file",
        description="Upload a file for chat messages"
    )
    def post(self, request, *args, **kwargs):
        # This would handle file upload for chat
        # Implementation depends on your file handling strategy
        return Response({"message": "File upload endpoint"})


class RoomParticipantsView(generics.ListAPIView):
    serializer_class = ChatRoomMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        room_id = self.kwargs['room_id']
        room = get_object_or_404(ChatRoom, id=room_id, participants=self.request.user)
        return ChatRoomMembership.objects.filter(room=room).select_related('user')

    @extend_schema(
        summary="List room participants",
        description="Get all participants in a chat room"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AddParticipantView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Add participant to room",
        description="Add a user to a chat room"
    )
    def post(self, request, *args, **kwargs):
        room_id = self.kwargs['room_id']
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
        user_to_add = get_object_or_404(User, id=user_id)
        
        try:
            ChatService.add_participant_to_room(room, user_to_add, request.user)
            return Response({"message": "Participant added successfully"})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RemoveParticipantView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Remove participant from room",
        description="Remove a user from a chat room"
    )
    def post(self, request, *args, **kwargs):
        room_id = self.kwargs['room_id']
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
        user_to_remove = get_object_or_404(User, id=user_id)
        
        try:
            ChatService.remove_participant_from_room(room, user_to_remove, request.user)
            return Response({"message": "Participant removed successfully"})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MessageSearchView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['content']

    def get_queryset(self):
        room_id = self.request.query_params.get('room_id')
        query = self.request.query_params.get('search', '')
        
        if not room_id or not query:
            return Message.objects.none()
        
        room = get_object_or_404(ChatRoom, id=room_id, participants=self.request.user)
        return ChatService.search_messages(room, query, self.request.user)

    @extend_schema(
        summary="Search messages",
        description="Search messages in a chat room"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(
    summary="Get chat statistics",
    description="Get general chat statistics for the current user"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def chat_stats_view(request):
    unread_count = ChatService.get_unread_messages_count(request.user)
    room_count = ChatRoom.objects.filter(participants=request.user).count()
    
    stats = {
        'unread_messages': unread_count,
        'total_rooms': room_count,
        'active_rooms': ChatRoom.objects.filter(participants=request.user, is_active=True).count()
    }
    
    return Response(stats)