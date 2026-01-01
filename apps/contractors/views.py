from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from django.shortcuts import get_object_or_404

from .models import Category, Skill, ContractorProfile, Portfolio, PortfolioImage, Certification
from .serializers import (
    CategorySerializer, SkillSerializer, ContractorProfileSerializer,
    ContractorProfileUpdateSerializer, ContractorListSerializer,
    PortfolioSerializer, PortfolioImageSerializer, CertificationSerializer
)
from .services import ContractorService
from .filters import ContractorFilter


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="List all categories",
        description="Get all active categories for contractor services"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SkillListView(generics.ListAPIView):
    queryset = Skill.objects.filter(is_active=True).select_related('category')
    serializer_class = SkillSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']

    @extend_schema(
        summary="List all skills",
        description="Get all active skills, optionally filtered by category"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ContractorListView(generics.ListAPIView):
    serializer_class = ContractorListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ContractorFilter
    search_fields = ['user__first_name', 'user__last_name', 'business_name', 'user__bio']
    ordering_fields = ['rating_average', 'hourly_rate_min', 'completed_projects', 'created_at']
    ordering = ['-rating_average', '-completed_projects']

    def get_queryset(self):
        return ContractorProfile.objects.select_related('user').prefetch_related(
            'categories', 'skills', 'portfolio_items__images'
        ).filter(user__is_active=True)

    @extend_schema(
        summary="List contractors",
        description="Search and filter contractors with various criteria",
        parameters=[
            OpenApiParameter(name='categories', description='Filter by category IDs', required=False),
            OpenApiParameter(name='min_rating', description='Minimum rating filter', required=False),
            OpenApiParameter(name='max_hourly_rate', description='Maximum hourly rate', required=False),
            OpenApiParameter(name='availability_only', description='Show only available contractors', required=False),
            OpenApiParameter(name='verified_only', description='Show only verified contractors', required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ContractorDetailView(generics.RetrieveAPIView):
    queryset = ContractorProfile.objects.select_related('user').prefetch_related(
        'categories', 'skills', 'portfolio_items__images', 'certifications'
    )
    serializer_class = ContractorProfileSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Get contractor details",
        description="Retrieve detailed information about a specific contractor"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ContractorProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ContractorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = ContractorProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'hourly_rate_min': 50,
                'hourly_rate_max': 100,
            }
        )
        return profile

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ContractorProfileUpdateSerializer
        return ContractorProfileSerializer

    @extend_schema(
        summary="Get my contractor profile",
        description="Retrieve current user's contractor profile"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update contractor profile",
        description="Update current user's contractor profile",
        request=ContractorProfileUpdateSerializer
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class PortfolioListCreateView(generics.ListCreateAPIView):
    serializer_class = PortfolioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        contractor_profile = get_object_or_404(ContractorProfile, user=self.request.user)
        return Portfolio.objects.filter(contractor=contractor_profile).prefetch_related('images')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        contractor_profile = get_object_or_404(ContractorProfile, user=self.request.user)
        context['contractor'] = contractor_profile
        return context

    @extend_schema(
        summary="List portfolio items",
        description="Get all portfolio items for the current contractor"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create portfolio item",
        description="Add a new portfolio item for the current contractor"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PortfolioDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PortfolioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        contractor_profile = get_object_or_404(ContractorProfile, user=self.request.user)
        return Portfolio.objects.filter(contractor=contractor_profile)

    @extend_schema(
        summary="Get portfolio item",
        description="Retrieve specific portfolio item"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update portfolio item",
        description="Update specific portfolio item"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete portfolio item",
        description="Delete specific portfolio item"
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class PortfolioImageUploadView(generics.CreateAPIView):
    serializer_class = PortfolioImageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        portfolio_id = self.kwargs['portfolio_id']
        contractor_profile = get_object_or_404(ContractorProfile, user=self.request.user)
        portfolio_item = get_object_or_404(
            Portfolio, 
            id=portfolio_id, 
            contractor=contractor_profile
        )
        serializer.save(portfolio_item=portfolio_item)

    @extend_schema(
        summary="Upload portfolio image",
        description="Upload an image for a specific portfolio item"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CertificationListCreateView(generics.ListCreateAPIView):
    serializer_class = CertificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        contractor_profile = get_object_or_404(ContractorProfile, user=self.request.user)
        return Certification.objects.filter(contractor=contractor_profile)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        contractor_profile = get_object_or_404(ContractorProfile, user=self.request.user)
        context['contractor'] = contractor_profile
        return context

    @extend_schema(
        summary="List certifications",
        description="Get all certifications for the current contractor"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Add certification",
        description="Add a new certification for the current contractor"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CertificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CertificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        contractor_profile = get_object_or_404(ContractorProfile, user=self.request.user)
        return Certification.objects.filter(contractor=contractor_profile)

    @extend_schema(
        summary="Get certification",
        description="Retrieve specific certification"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update certification",
        description="Update specific certification"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete certification",
        description="Delete specific certification"
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


@extend_schema(
    summary="Get contractor statistics",
    description="Get general statistics about contractors on the platform"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def contractor_stats_view(request):
    stats = ContractorService.get_contractor_stats()
    return Response(stats)


@extend_schema(
    summary="Get recommended contractors",
    description="Get personalized contractor recommendations for the current user"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def recommended_contractors_view(request):
    contractors = ContractorService.get_recommended_contractors(request.user)
    serializer = ContractorListSerializer(contractors, many=True)
    return Response(serializer.data)