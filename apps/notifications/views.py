from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Notification, NotificationPreference
from .serializers import (
    NotificationSerializer, NotificationPreferenceSerializer,
    BulkNotificationActionSerializer
)
from .services import NotificationService


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['notification_type', 'is_read']
    ordering = ['-created_at']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @extend_schema(
        summary="List notifications",
        description="Get all notifications for the current user"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class NotificationDetailView(generics.RetrieveAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @extend_schema(
        summary="Get notification details",
        description="Retrieve specific notification details"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MarkNotificationReadView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Mark notification as read",
        description="Mark a specific notification as read"
    )
    def patch(self, request, *args, **kwargs):
        notification_id = self.kwargs['pk']
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.mark_as_read()
            return Response({"message": "Notification marked as read"})
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)


class MarkAllNotificationsReadView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Mark all notifications as read",
        description="Mark all unread notifications as read for the current user"
    )
    def patch(self, request, *args, **kwargs):
        updated_count = NotificationService.mark_notifications_as_read(request.user)
        return Response({
            "message": f"{updated_count} notifications marked as read"
        })


class UnreadNotificationCountView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get unread notification count",
        description="Get the count of unread notifications for the current user"
    )
    def get(self, request, *args, **kwargs):
        count = NotificationService.get_unread_count(request.user)
        return Response({"unread_count": count})


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        preference, created = NotificationPreference.objects.get_or_create(
            user=self.request.user,
            defaults={
                'email_project_updates': True,
                'email_new_messages': True,
                'email_applications': True,
                'email_reviews': True,
                'push_project_updates': True,
                'push_new_messages': True,
                'push_applications': True,
                'push_reviews': True,
            }
        )
        return preference

    @extend_schema(
        summary="Get notification preferences",
        description="Retrieve current user's notification preferences"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update notification preferences",
        description="Update current user's notification preferences"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class BulkMarkReadView(generics.UpdateAPIView):
    serializer_class = BulkNotificationActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Bulk mark notifications as read",
        description="Mark multiple notifications as read"
    )
    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            notification_ids = serializer.validated_data['notification_ids']
            updated_count = NotificationService.mark_notifications_as_read(
                request.user, notification_ids
            )
            return Response({
                "message": f"{updated_count} notifications marked as read"
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkDeleteView(generics.DestroyAPIView):
    serializer_class = BulkNotificationActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Bulk delete notifications",
        description="Delete multiple notifications"
    )
    def delete(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            notification_ids = serializer.validated_data['notification_ids']
            deleted_count = Notification.objects.filter(
                id__in=notification_ids,
                user=request.user
            ).delete()[0]
            return Response({
                "message": f"{deleted_count} notifications deleted"
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get notification statistics",
    description="Get notification statistics for the current user"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_stats_view(request):
    user = request.user
    stats = {
        'total_notifications': Notification.objects.filter(user=user).count(),
        'unread_notifications': Notification.objects.filter(user=user, is_read=False).count(),
        'notifications_by_type': {}
    }
    
    # Get count by notification type
    for notification_type, _ in Notification.NOTIFICATION_TYPES:
        count = Notification.objects.filter(
            user=user, 
            notification_type=notification_type
        ).count()
        stats['notifications_by_type'][notification_type] = count
    
    return Response(stats)