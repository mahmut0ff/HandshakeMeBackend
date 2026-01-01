from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Avg, Count

from .models import Review, ReviewImage, ReviewResponse, ReviewHelpful
from .serializers import (
    ReviewSerializer, ReviewCreateSerializer, ReviewResponseSerializer,
    ReviewImageSerializer, ReviewHelpfulSerializer
)
from apps.contractors.models import ContractorProfile


class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['rating', 'is_verified', 'is_public']
    ordering = ['-created_at']

    def get_queryset(self):
        return Review.objects.filter(is_public=True).select_related(
            'client', 'contractor__user', 'project'
        ).prefetch_related('images')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ReviewCreateSerializer
        return ReviewSerializer

    @extend_schema(
        summary="List reviews",
        description="Get all public reviews with filtering options"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create review",
        description="Create a new review for a contractor"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only access their own reviews or public reviews
        return Review.objects.filter(
            models.Q(client=self.request.user) | models.Q(is_public=True)
        ).select_related('client', 'contractor__user', 'project').prefetch_related('images')

    @extend_schema(
        summary="Get review details",
        description="Retrieve specific review details"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update review",
        description="Update a review (only by the review author)"
    )
    def patch(self, request, *args, **kwargs):
        review = self.get_object()
        if review.client != request.user:
            return Response(
                {"error": "You can only update your own reviews"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().patch(request, *args, **kwargs)


class ReviewResponseCreateView(generics.CreateAPIView):
    serializer_class = ReviewResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        review_id = self.kwargs['pk']
        review = get_object_or_404(Review, id=review_id)
        
        # Only the contractor can respond to their review
        if review.contractor.user != self.request.user:
            raise PermissionError("Only the contractor can respond to their review")
        
        serializer.save(review=review, contractor=self.request.user)

    @extend_schema(
        summary="Create review response",
        description="Create a response to a review (only by the contractor)"
    )
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)


class ReviewHelpfulView(generics.CreateAPIView):
    serializer_class = ReviewHelpfulSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        review_id = self.kwargs['pk']
        review = get_object_or_404(Review, id=review_id)
        
        # Update or create helpful vote
        helpful_vote, created = ReviewHelpful.objects.update_or_create(
            review=review,
            user=self.request.user,
            defaults={'is_helpful': serializer.validated_data['is_helpful']}
        )
        
        return helpful_vote

    @extend_schema(
        summary="Vote on review helpfulness",
        description="Mark a review as helpful or not helpful"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ReviewImageUploadView(generics.CreateAPIView):
    serializer_class = ReviewImageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        review_id = self.kwargs['review_id']
        review = get_object_or_404(Review, id=review_id, client=self.request.user)
        serializer.save(review=review)

    @extend_schema(
        summary="Upload review image",
        description="Upload an image for a specific review"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ContractorReviewListView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['rating', 'is_verified']
    ordering = ['-created_at']

    def get_queryset(self):
        contractor_id = self.kwargs['contractor_id']
        contractor = get_object_or_404(ContractorProfile, id=contractor_id)
        return Review.objects.filter(
            contractor=contractor,
            is_public=True
        ).select_related('client', 'project').prefetch_related('images')

    @extend_schema(
        summary="List contractor reviews",
        description="Get all public reviews for a specific contractor"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(
    summary="Get review statistics",
    description="Get general review statistics"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def review_stats_view(request):
    stats = {
        'total_reviews': Review.objects.filter(is_public=True).count(),
        'verified_reviews': Review.objects.filter(is_public=True, is_verified=True).count(),
        'average_rating': Review.objects.filter(is_public=True).aggregate(
            avg_rating=Avg('rating')
        )['avg_rating'] or 0,
        'rating_distribution': {}
    }
    
    # Get rating distribution
    for rating in range(1, 6):
        count = Review.objects.filter(is_public=True, rating=rating).count()
        stats['rating_distribution'][str(rating)] = count
    
    return Response(stats)


@extend_schema(
    summary="Get contractor review statistics",
    description="Get review statistics for a specific contractor"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def contractor_review_stats_view(request, contractor_id):
    contractor = get_object_or_404(ContractorProfile, id=contractor_id)
    reviews = Review.objects.filter(contractor=contractor, is_public=True)
    
    stats = {
        'total_reviews': reviews.count(),
        'verified_reviews': reviews.filter(is_verified=True).count(),
        'average_rating': reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
        'rating_distribution': {},
        'category_ratings': {
            'quality': reviews.exclude(quality_rating__isnull=True).aggregate(
                avg=Avg('quality_rating')
            )['avg'] or 0,
            'communication': reviews.exclude(communication_rating__isnull=True).aggregate(
                avg=Avg('communication_rating')
            )['avg'] or 0,
            'timeliness': reviews.exclude(timeliness_rating__isnull=True).aggregate(
                avg=Avg('timeliness_rating')
            )['avg'] or 0,
            'professionalism': reviews.exclude(professionalism_rating__isnull=True).aggregate(
                avg=Avg('professionalism_rating')
            )['avg'] or 0,
        }
    }
    
    # Get rating distribution
    for rating in range(1, 6):
        count = reviews.filter(rating=rating).count()
        stats['rating_distribution'][str(rating)] = count
    
    return Response(stats)