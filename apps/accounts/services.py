from django.utils import timezone
from django.core.cache import cache
from django.db import models
from .models import User


class UserService:
    """Service class for user-related business logic"""
    
    @staticmethod
    def update_user_online_status(user, is_online=True):
        """Update user's online status and last seen timestamp"""
        user.is_online = is_online
        user.last_seen = timezone.now()
        user.save(update_fields=['is_online', 'last_seen'])
        
        # Cache online status for quick access
        cache_key = f"user_online_{user.id}"
        if is_online:
            cache.set(cache_key, True, timeout=300)  # 5 minutes
        else:
            cache.delete(cache_key)
    
    @staticmethod
    def is_user_online(user_id):
        """Check if user is online using cache first, then database"""
        cache_key = f"user_online_{user_id}"
        is_online = cache.get(cache_key)
        
        if is_online is None:
            try:
                user = User.objects.get(id=user_id)
                is_online = user.is_online
                if is_online:
                    cache.set(cache_key, True, timeout=300)
            except User.DoesNotExist:
                is_online = False
        
        return is_online
    
    @staticmethod
    def get_user_profile_data(user):
        """Get comprehensive user profile data"""
        return {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'full_name': user.full_name,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number,
            'user_type': user.user_type,
            'avatar': user.avatar.url if user.avatar else None,
            'bio': user.bio,
            'location': user.location,
            'is_verified': user.is_verified,
            'is_online': user.is_online,
            'last_seen': user.last_seen,
            'created_at': user.created_at,
        }
    
    @staticmethod
    def search_users(query, user_type=None, limit=20):
        """Search users by name, email, or username"""
        users = User.objects.filter(is_active=True)
        
        if user_type:
            users = users.filter(user_type=user_type)
        
        if query:
            users = users.filter(
                models.Q(first_name__icontains=query) |
                models.Q(last_name__icontains=query) |
                models.Q(username__icontains=query) |
                models.Q(email__icontains=query)
            )
        
        return users[:limit]