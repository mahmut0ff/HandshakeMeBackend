from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from .models import Advertisement, AdCategory
from .serializers import AdvertisementSerializer, AdCategorySerializer


class AdvertisementListView(generics.ListAPIView):
    serializer_class = AdvertisementSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Advertisement.objects.filter(
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        )
        
        position = self.request.query_params.get('position')
        target_audience = self.request.query_params.get('target_audience', 'all')
        
        if position:
            queryset = queryset.filter(position=position)
        
        # Filter by target audience
        if hasattr(self.request.user, 'user_type') and self.request.user.is_authenticated:
            user_type = self.request.user.user_type
            if user_type == 'contractor':
                queryset = queryset.filter(target_audience__in=['all', 'contractors'])
            elif user_type == 'client':
                queryset = queryset.filter(target_audience__in=['all', 'clients'])
        else:
            queryset = queryset.filter(target_audience='all')
        
        return queryset.order_by('-priority', '-created_at')

    @extend_schema(
        summary="List active advertisements",
        description="Get active advertisements filtered by position and target audience"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(
    summary="Track advertisement impression",
    description="Increment impression count for an advertisement"
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def track_impression(request, ad_id):
    try:
        ad = Advertisement.objects.get(id=ad_id, is_active=True)
        ad.increment_impressions()
        return Response({'message': 'Impression tracked'})
    except Advertisement.DoesNotExist:
        return Response({'error': 'Advertisement not found'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    summary="Track advertisement click",
    description="Increment click count for an advertisement"
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def track_click(request, ad_id):
    try:
        ad = Advertisement.objects.get(id=ad_id, is_active=True)
        ad.increment_clicks()
        return Response({'message': 'Click tracked'})
    except Advertisement.DoesNotExist:
        return Response({'error': 'Advertisement not found'}, status=status.HTTP_404_NOT_FOUND)


class AdCategoryListView(generics.ListAPIView):
    queryset = AdCategory.objects.filter(is_active=True)
    serializer_class = AdCategorySerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="List advertisement categories",
        description="Get all active advertisement categories"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)