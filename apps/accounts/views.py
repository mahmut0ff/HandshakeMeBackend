from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import update_session_auth_hash
from django.db.models import Avg, Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User, Address
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserUpdateSerializer, ChangePasswordSerializer, AddressSerializer
)
from .services import UserService


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new user",
        description="Create a new user account with email and password",
        responses={
            201: OpenApiResponse(description="User created successfully"),
            400: OpenApiResponse(description="Validation errors")
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Login user",
    description="Authenticate user and return JWT tokens",
    request=UserLoginSerializer,
    responses={
        200: OpenApiResponse(description="Login successful"),
        400: OpenApiResponse(description="Invalid credentials")
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        UserService.update_user_online_status(user, True)
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Logout user",
    description="Logout user and blacklist refresh token",
    responses={
        200: OpenApiResponse(description="Logout successful"),
        400: OpenApiResponse(description="Invalid token")
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        UserService.update_user_online_status(request.user, False)
        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    @extend_schema(
        summary="Get user profile",
        description="Retrieve current user's profile information"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update user profile",
        description="Update current user's profile information",
        request=UserUpdateSerializer
    )
    def patch(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(self.get_object(), data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserProfileSerializer(self.get_object()).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Change password",
    description="Change user's password",
    request=ChangePasswordSerializer,
    responses={
        200: OpenApiResponse(description="Password changed successfully"),
        400: OpenApiResponse(description="Validation errors")
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        update_session_auth_hash(request, user)
        return Response({"message": "Password changed successfully"})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get user profile statistics",
    description="Get user statistics like completed projects, reviews, etc.",
    responses={
        200: OpenApiResponse(description="Statistics retrieved successfully")
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_stats_view(request):
    user = request.user
    
    # Get basic stats
    stats = {
        'completed_projects': 0,
        'total_reviews': 0,
        'average_rating': 0.0,
        'member_since': user.date_joined.year
    }
    
    # If user is a contractor, get project and review stats
    if hasattr(user, 'contractor_profile'):
        from apps.projects.models import Project
        from apps.reviews.models import Review
        
        # Count completed projects
        completed_projects = Project.objects.filter(
            contractor=user,
            status='completed'
        ).count()
        
        # Get review stats
        reviews = Review.objects.filter(contractor=user)
        review_stats = reviews.aggregate(
            total=Count('id'),
            avg_rating=Avg('rating')
        )
        
        stats.update({
            'completed_projects': completed_projects,
            'total_reviews': review_stats['total'] or 0,
            'average_rating': float(review_stats['avg_rating'] or 0.0),
        })
    
    return Response(stats)


@extend_schema(
    summary="Upload profile avatar",
    description="Upload a new profile avatar image",
    responses={
        200: OpenApiResponse(description="Avatar uploaded successfully"),
        400: OpenApiResponse(description="Invalid file")
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def avatar_upload_view(request):
    if 'avatar' not in request.FILES:
        return Response({'error': 'No avatar file provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    avatar_file = request.FILES['avatar']
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if avatar_file.content_type not in allowed_types:
        return Response({'error': 'Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed.'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Validate file size (max 5MB)
    if avatar_file.size > 5 * 1024 * 1024:
        return Response({'error': 'File too large. Maximum size is 5MB.'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Save avatar
    user = request.user
    user.avatar = avatar_file
    user.save()
    
    return Response({
        'avatar': user.avatar.url if user.avatar else None,
        'message': 'Avatar uploaded successfully'
    })


class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    @extend_schema(
        summary="List user addresses",
        description="Get all addresses for the current user"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create new address",
        description="Add a new address for the current user"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    @extend_schema(
        summary="Get address details",
        description="Retrieve specific address details"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update address",
        description="Update specific address"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete address",
        description="Delete specific address"
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)