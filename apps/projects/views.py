from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.shortcuts import get_object_or_404

from .models import Project, ProjectImage, ProjectApplication, ProjectMilestone, ProjectUpdate, ProjectDocument
from .serializers import (
    ProjectListSerializer, ProjectDetailSerializer, ProjectCreateUpdateSerializer,
    ProjectStatusUpdateSerializer, ProjectApplicationSerializer, ProjectApplicationCreateSerializer,
    ProjectMilestoneSerializer, ProjectUpdateSerializer, ProjectDocumentSerializer,
    ProjectImageSerializer
)
from .services import ProjectService
from .filters import ProjectFilter
from apps.contractors.models import ContractorProfile


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProjectFilter
    search_fields = ['title', 'description', 'city', 'state']
    ordering_fields = ['created_at', 'deadline', 'budget_min', 'budget_max']
    ordering = ['-created_at']

    def get_queryset(self):
        return Project.objects.select_related('client', 'contractor__user', 'category').prefetch_related('images')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectCreateUpdateSerializer
        return ProjectListSerializer

    @extend_schema(
        summary="List projects",
        description="Get all projects with filtering and search capabilities"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create project",
        description="Create a new project",
        request=ProjectCreateUpdateSerializer
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.select_related('client', 'contractor__user', 'category').prefetch_related(
        'images', 'milestones', 'updates', 'documents', 'applications__contractor__user'
    )
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProjectCreateUpdateSerializer
        return ProjectDetailSerializer

    def get_object(self):
        obj = super().get_object()
        # Increment view count if it's a GET request
        if self.request.method == 'GET':
            ProjectService.increment_project_views(obj)
        return obj

    @extend_schema(
        summary="Get project details",
        description="Retrieve detailed information about a specific project"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update project",
        description="Update project information",
        request=ProjectCreateUpdateSerializer
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class ProjectStatusUpdateView(generics.UpdateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        # Only project owner can update status
        if obj.client != self.request.user:
            self.permission_denied(self.request, message="Only project owner can update status")
        return obj

    @extend_schema(
        summary="Update project status",
        description="Update project status and progress",
        request=ProjectStatusUpdateSerializer
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class ProjectApplicationCreateView(generics.CreateAPIView):
    serializer_class = ProjectApplicationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        project = get_object_or_404(Project, id=self.kwargs['project_id'])
        contractor_profile = get_object_or_404(ContractorProfile, user=self.request.user)
        context['project'] = project
        context['contractor'] = contractor_profile
        return context

    @extend_schema(
        summary="Apply to project",
        description="Submit an application to a project"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ProjectApplicationListView(generics.ListAPIView):
    serializer_class = ProjectApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project = get_object_or_404(Project, id=self.kwargs['project_id'])
        # Only project owner can see applications
        if project.client != self.request.user:
            return ProjectApplication.objects.none()
        return ProjectApplication.objects.filter(project=project).select_related('contractor__user')

    @extend_schema(
        summary="List project applications",
        description="Get all applications for a specific project"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AcceptApplicationView(generics.UpdateAPIView):
    queryset = ProjectApplication.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Accept project application",
        description="Accept a contractor's application to a project"
    )
    def patch(self, request, *args, **kwargs):
        application = self.get_object()
        try:
            ProjectService.accept_application(application.project, application.id, request.user)
            return Response({"message": "Application accepted successfully"})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RejectApplicationView(generics.UpdateAPIView):
    queryset = ProjectApplication.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Reject project application",
        description="Reject a contractor's application to a project"
    )
    def patch(self, request, *args, **kwargs):
        application = self.get_object()
        if application.project.client != request.user:
            return Response({"error": "Only project owner can reject applications"}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        application.status = 'rejected'
        application.save()
        return Response({"message": "Application rejected successfully"})


class ProjectImageUploadView(generics.CreateAPIView):
    serializer_class = ProjectImageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        project_id = self.kwargs['project_id']
        project = get_object_or_404(Project, id=project_id, client=self.request.user)
        serializer.save(project=project)

    @extend_schema(
        summary="Upload project image",
        description="Upload an image for a specific project"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ProjectMilestoneListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectMilestoneSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project = get_object_or_404(Project, id=self.kwargs['project_id'])
        return ProjectMilestone.objects.filter(project=project)

    def perform_create(self, serializer):
        project = get_object_or_404(Project, id=self.kwargs['project_id'])
        serializer.save(project=project)

    @extend_schema(
        summary="List project milestones",
        description="Get all milestones for a specific project"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create project milestone",
        description="Add a new milestone to a project"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ProjectMilestoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProjectMilestone.objects.all()
    serializer_class = ProjectMilestoneSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get milestone details",
        description="Retrieve specific milestone details"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ProjectUpdateListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project = get_object_or_404(Project, id=self.kwargs['project_id'])
        return ProjectUpdate.objects.filter(project=project).select_related('author')

    def perform_create(self, serializer):
        project = get_object_or_404(Project, id=self.kwargs['project_id'])
        serializer.save(project=project)

    @extend_schema(
        summary="List project updates",
        description="Get all updates for a specific project"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create project update",
        description="Add a new update to a project"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ProjectDocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project = get_object_or_404(Project, id=self.kwargs['project_id'])
        return ProjectDocument.objects.filter(project=project).select_related('uploaded_by')

    def perform_create(self, serializer):
        project = get_object_or_404(Project, id=self.kwargs['project_id'])
        serializer.save(project=project)

    @extend_schema(
        summary="List project documents",
        description="Get all documents for a specific project"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Upload project document",
        description="Upload a document for a specific project"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ProjectDocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProjectDocument.objects.all()
    serializer_class = ProjectDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get document details",
        description="Retrieve specific document details"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(
    summary="Get project statistics",
    description="Get general statistics about projects on the platform"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def project_stats_view(request):
    stats = ProjectService.get_project_stats()
    return Response(stats)


@extend_schema(
    summary="Get recommended projects",
    description="Get personalized project recommendations for the current contractor"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def recommended_projects_view(request):
    try:
        contractor_profile = ContractorProfile.objects.get(user=request.user)
        projects = ProjectService.get_recommended_projects_for_contractor(contractor_profile)
        serializer = ProjectListSerializer(projects, many=True)
        return Response(serializer.data)
    except ContractorProfile.DoesNotExist:
        return Response({"error": "Contractor profile not found"}, status=status.HTTP_404_NOT_FOUND)