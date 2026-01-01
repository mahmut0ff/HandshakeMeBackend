from django.db import models
from apps.accounts.models import User


class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('direct', 'Direct Message'),
        ('project', 'Project Chat'),
        ('group', 'Group Chat'),
    ]

    name = models.CharField(max_length=200, blank=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='direct')
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    project = models.ForeignKey(
        'projects.Project', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='chat_rooms'
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_rooms'
        verbose_name = 'Chat Room'
        verbose_name_plural = 'Chat Rooms'
        ordering = ['-updated_at']

    def __str__(self):
        if self.name:
            return self.name
        elif self.room_type == 'direct':
            participants = list(self.participants.all()[:2])
            if len(participants) == 2:
                return f"{participants[0].full_name} & {participants[1].full_name}"
        elif self.project:
            return f"Project: {self.project.title}"
        return f"Room #{self.id}"

    @property
    def room_id(self):
        return f"room_{self.id}"

    def get_last_message(self):
        return self.messages.first()

    def get_unread_count_for_user(self, user):
        return self.messages.filter(
            read_by__isnull=True
        ).exclude(sender=user).count()


class Message(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('system', 'System'),
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    
    # Message metadata
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender.full_name}: {self.content[:50]}..."

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update room's updated_at timestamp
        self.room.save(update_fields=['updated_at'])


class MessageReadStatus(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_status')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message_read_status'
        unique_together = ['message', 'user']
        verbose_name = 'Message Read Status'
        verbose_name_plural = 'Message Read Statuses'

    def __str__(self):
        return f"{self.user.full_name} read message {self.message.id}"


class ChatRoomMembership(models.Model):
    ROLES = [
        ('member', 'Member'),
        ('admin', 'Admin'),
        ('owner', 'Owner'),
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_memberships')
    role = models.CharField(max_length=10, choices=ROLES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    is_muted = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        db_table = 'chat_room_memberships'
        unique_together = ['room', 'user']
        verbose_name = 'Chat Room Membership'
        verbose_name_plural = 'Chat Room Memberships'

    def __str__(self):
        return f"{self.user.full_name} in {self.room}"