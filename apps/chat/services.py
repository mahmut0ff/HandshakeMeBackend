from django.db.models import Q, Count, Max, Prefetch
from django.utils import timezone
from .models import ChatRoom, Message, MessageReadStatus, ChatRoomMembership
from apps.accounts.models import User


class ChatService:
    """Service class for chat-related business logic"""
    
    @staticmethod
    def get_or_create_direct_room(user1, user2):
        """Get or create a direct message room between two users"""
        # Check if a direct room already exists between these users
        existing_room = ChatRoom.objects.filter(
            room_type='direct',
            participants=user1
        ).filter(participants=user2).first()
        
        if existing_room:
            return existing_room
        
        # Create new direct room
        room = ChatRoom.objects.create(
            room_type='direct',
            created_by=user1
        )
        room.participants.add(user1, user2)
        
        # Create memberships
        ChatRoomMembership.objects.create(room=room, user=user1, role='member')
        ChatRoomMembership.objects.create(room=room, user=user2, role='member')
        
        return room
    
    @staticmethod
    def create_project_room(project, created_by):
        """Create a chat room for a project"""
        room = ChatRoom.objects.create(
            name=f"Project: {project.title}",
            room_type='project',
            project=project,
            created_by=created_by
        )
        
        # Add client and contractor as participants
        participants = [project.client]
        if project.contractor:
            participants.append(project.contractor.user)
        
        room.participants.add(*participants)
        
        # Create memberships
        for user in participants:
            role = 'owner' if user == created_by else 'member'
            ChatRoomMembership.objects.create(room=room, user=user, role=role)
        
        return room
    
    @staticmethod
    def get_user_chat_rooms(user, limit=50):
        """Get all chat rooms for a user with latest message info"""
        rooms = ChatRoom.objects.filter(
            participants=user,
            is_active=True
        ).select_related('project', 'created_by').prefetch_related(
            'participants',
            Prefetch(
                'messages',
                queryset=Message.objects.select_related('sender').order_by('-created_at')[:1],
                to_attr='latest_messages'
            )
        ).annotate(
            unread_count=Count(
                'messages',
                filter=Q(
                    messages__read_status__isnull=True,
                    messages__sender__ne=user
                )
            )
        ).order_by('-updated_at')[:limit]
        
        return rooms
    
    @staticmethod
    def get_room_messages(room, user, limit=50, before_message_id=None):
        """Get messages for a room with pagination"""
        messages = Message.objects.filter(room=room).select_related(
            'sender', 'reply_to__sender'
        ).prefetch_related('read_status')
        
        if before_message_id:
            messages = messages.filter(id__lt=before_message_id)
        
        messages = messages.order_by('-created_at')[:limit]
        
        # Mark messages as read for the requesting user
        unread_messages = messages.exclude(sender=user).exclude(
            read_status__user=user
        )
        
        read_statuses = []
        for message in unread_messages:
            read_statuses.append(
                MessageReadStatus(message=message, user=user)
            )
        
        if read_statuses:
            MessageReadStatus.objects.bulk_create(read_statuses, ignore_conflicts=True)
        
        return list(reversed(messages))
    
    @staticmethod
    def send_message(room, sender, content, message_type='text', reply_to=None, file=None, image=None):
        """Send a message to a room"""
        # Check if sender is a participant
        if not room.participants.filter(id=sender.id).exists():
            raise ValueError("User is not a participant in this room")
        
        message = Message.objects.create(
            room=room,
            sender=sender,
            content=content,
            message_type=message_type,
            reply_to=reply_to,
            file=file,
            image=image
        )
        
        return message
    
    @staticmethod
    def add_participant_to_room(room, user, added_by, role='member'):
        """Add a participant to a chat room"""
        # Check if the user adding has permission (admin or owner)
        membership = ChatRoomMembership.objects.filter(
            room=room,
            user=added_by,
            role__in=['admin', 'owner']
        ).first()
        
        if not membership and room.room_type != 'direct':
            raise ValueError("You don't have permission to add participants")
        
        # Add user to room
        room.participants.add(user)
        
        # Create membership
        ChatRoomMembership.objects.get_or_create(
            room=room,
            user=user,
            defaults={'role': role}
        )
        
        # Send system message
        ChatService.send_system_message(
            room,
            f"{user.full_name} was added to the chat by {added_by.full_name}"
        )
    
    @staticmethod
    def remove_participant_from_room(room, user, removed_by):
        """Remove a participant from a chat room"""
        # Check permissions
        if user != removed_by:  # Users can always remove themselves
            membership = ChatRoomMembership.objects.filter(
                room=room,
                user=removed_by,
                role__in=['admin', 'owner']
            ).first()
            
            if not membership:
                raise ValueError("You don't have permission to remove participants")
        
        # Remove user from room
        room.participants.remove(user)
        
        # Delete membership
        ChatRoomMembership.objects.filter(room=room, user=user).delete()
        
        # Send system message
        action = "left" if user == removed_by else "was removed from"
        ChatService.send_system_message(
            room,
            f"{user.full_name} {action} the chat"
        )
    
    @staticmethod
    def send_system_message(room, content):
        """Send a system message to a room"""
        Message.objects.create(
            room=room,
            sender=None,  # System messages have no sender
            content=content,
            message_type='system'
        )
    
    @staticmethod
    def search_messages(room, query, user, limit=20):
        """Search messages in a room"""
        messages = Message.objects.filter(
            room=room,
            content__icontains=query
        ).select_related('sender').order_by('-created_at')[:limit]
        
        return messages
    
    @staticmethod
    def get_room_participants_status(room):
        """Get online status of room participants"""
        participants = room.participants.all()
        participant_status = []
        
        for participant in participants:
            membership = ChatRoomMembership.objects.filter(
                room=room,
                user=participant
            ).first()
            
            participant_status.append({
                'user': participant,
                'is_online': participant.is_online,
                'last_seen': participant.last_seen,
                'role': membership.role if membership else 'member',
                'last_seen_in_room': membership.last_seen_at if membership else None
            })
        
        return participant_status
    
    @staticmethod
    def get_unread_messages_count(user):
        """Get total unread messages count for a user"""
        return Message.objects.filter(
            room__participants=user,
            read_status__isnull=True
        ).exclude(sender=user).count()