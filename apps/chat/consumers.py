import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import ChatRoom, Message, MessageReadStatus
from .services import ChatService


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        # Check if user has access to this room
        has_access = await self.check_room_access()
        if not has_access:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Update user's last seen in room
        await self.update_last_seen()

        # Send user online status to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'status': 'online'
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # Send user offline status to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'status': 'offline'
                }
            )

            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')

            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_message':
                await self.handle_read_message(data)
            elif message_type == 'edit_message':
                await self.handle_edit_message(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))

    async def handle_message(self, data):
        content = data.get('content', '').strip()
        reply_to_id = data.get('reply_to')
        
        if not content:
            return

        # Save message to database
        message = await self.save_message(content, reply_to_id)
        
        if message:
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': await self.serialize_message(message)
                }
            )

    async def handle_typing(self, data):
        is_typing = data.get('is_typing', False)
        
        # Send typing indicator to room group (exclude sender)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'user_name': self.user.full_name,
                'is_typing': is_typing
            }
        )

    async def handle_read_message(self, data):
        message_id = data.get('message_id')
        if message_id:
            await self.mark_message_as_read(message_id)

    async def handle_edit_message(self, data):
        message_id = data.get('message_id')
        new_content = data.get('content', '').strip()
        
        if message_id and new_content:
            message = await self.edit_message(message_id, new_content)
            if message:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_edited',
                        'message': await self.serialize_message(message)
                    }
                )

    # Receive message from room group
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))

    async def typing_indicator(self, event):
        # Don't send typing indicator to the sender
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'user_name': event['user_name'],
                'is_typing': event['is_typing']
            }))

    async def user_status(self, event):
        # Don't send status update to the user themselves
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_status',
                'user_id': event['user_id'],
                'status': event['status']
            }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message': event['message']
        }))

    @database_sync_to_async
    def check_room_access(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return room.participants.filter(id=self.user.id).exists()
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content, reply_to_id=None):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            
            reply_to = None
            if reply_to_id:
                try:
                    reply_to = Message.objects.get(id=reply_to_id, room=room)
                except Message.DoesNotExist:
                    pass

            message = Message.objects.create(
                room=room,
                sender=self.user,
                content=content,
                reply_to=reply_to
            )
            return message
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        return {
            'id': message.id,
            'content': message.content,
            'sender': {
                'id': message.sender.id,
                'name': message.sender.full_name,
                'avatar': message.sender.avatar.url if message.sender.avatar else None
            },
            'message_type': message.message_type,
            'reply_to': {
                'id': message.reply_to.id,
                'content': message.reply_to.content[:100],
                'sender_name': message.reply_to.sender.full_name
            } if message.reply_to else None,
            'is_edited': message.is_edited,
            'edited_at': message.edited_at.isoformat() if message.edited_at else None,
            'created_at': message.created_at.isoformat()
        }

    @database_sync_to_async
    def update_last_seen(self):
        from .models import ChatRoomMembership
        try:
            membership = ChatRoomMembership.objects.get(
                room_id=self.room_id,
                user=self.user
            )
            membership.save(update_fields=['last_seen_at'])
        except ChatRoomMembership.DoesNotExist:
            pass

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        try:
            message = Message.objects.get(id=message_id, room_id=self.room_id)
            MessageReadStatus.objects.get_or_create(
                message=message,
                user=self.user
            )
        except Message.DoesNotExist:
            pass

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        try:
            message = Message.objects.get(
                id=message_id,
                room_id=self.room_id,
                sender=self.user
            )
            message.content = new_content
            message.is_edited = True
            from django.utils import timezone
            message.edited_at = timezone.now()
            message.save()
            return message
        except Message.DoesNotExist:
            return None