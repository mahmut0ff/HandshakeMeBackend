from rest_framework import serializers
from apps.accounts.serializers import UserProfileSerializer
from apps.contractors.serializers import ContractorListSerializer, CategorySerializer
from .models import (
    Project, ProjectImage, ProjectApplication, ProjectMilestone, 
    ProjectUpdate, ProjectDocument
)


class ProjectImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectImage
        fields = ('id', 'image', 'caption', 'is_primary', 'created_at')


class ProjectMilestoneSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = ProjectMilestone
        fields = (
            'id', 'title', 'description', 'due_date', 'completion_date',
            'status', 'payment_percentage', 'order', 'is_overdue',
            'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')


class ProjectUpdateSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    milestone_title = serializers.CharField(source='milestone.title', read_only=True)
    
    class Meta:
        model = ProjectUpdate
        fields = (
            'id', 'author', 'title', 'content', 'progress_percentage',
            'is_milestone_update', 'milestone', 'milestone_title', 'created_at'
        )
        read_only_fields = ('author', 'created_at')

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class ProjectDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = ProjectDocument
        fields = (
            'id', 'title', 'document_type', 'file', 'description',
            'uploaded_by', 'is_private', 'created_at'
        )
        read_only_fields = ('uploaded_by', 'created_at')

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


class ProjectApplicationSerializer(serializers.ModelSerializer):
    contractor = ContractorListSerializer(read_only=True)
    
    class Meta:
        model = ProjectApplication
        fields = (
            'id', 'contractor', 'cover_letter', 'proposed_budget',
            'proposed_timeline', 'status', 'applied_at', 'updated_at'
        )
        read_only_fields = ('contractor', 'applied_at', 'updated_at')


class ProjectApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectApplication
        fields = ('cover_letter', 'proposed_budget', 'proposed_timeline')

    def create(self, validated_data):
        validated_data['contractor'] = self.context['contractor']
        validated_data['project'] = self.context['project']
        return super().create(validated_data)


class ProjectListSerializer(serializers.ModelSerializer):
    """Simplified serializer for project listings"""
    client = UserProfileSerializer(read_only=True)
    contractor = ContractorListSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    average_budget = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    applications_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Project
        fields = (
            'id', 'title', 'description', 'client', 'contractor', 'category',
            'budget_min', 'budget_max', 'average_budget', 'status', 'priority',
            'city', 'state', 'deadline', 'progress_percentage', 'is_active',
            'primary_image', 'views_count', 'applications_count', 'created_at'
        )

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if not primary_image:
            primary_image = obj.images.first()
        
        if primary_image:
            return {
                'id': primary_image.id,
                'image': primary_image.image.url,
                'caption': primary_image.caption
            }
        return None


class ProjectDetailSerializer(serializers.ModelSerializer):
    client = UserProfileSerializer(read_only=True)
    contractor = ContractorListSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = ProjectImageSerializer(many=True, read_only=True)
    milestones = ProjectMilestoneSerializer(many=True, read_only=True)
    updates = ProjectUpdateSerializer(many=True, read_only=True)
    documents = ProjectDocumentSerializer(many=True, read_only=True)
    applications = ProjectApplicationSerializer(many=True, read_only=True)
    average_budget = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Project
        fields = (
            'id', 'title', 'description', 'client', 'contractor', 'category',
            'budget_min', 'budget_max', 'average_budget', 'status', 'priority',
            'address', 'city', 'state', 'postal_code', 'latitude', 'longitude',
            'start_date', 'end_date', 'deadline', 'progress_percentage',
            'is_featured', 'is_active', 'views_count', 'applications_count',
            'images', 'milestones', 'updates', 'documents', 'applications',
            'created_at', 'updated_at'
        )


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            'title', 'description', 'category', 'budget_min', 'budget_max',
            'priority', 'address', 'city', 'state', 'postal_code',
            'latitude', 'longitude', 'start_date', 'end_date', 'deadline'
        )

    def create(self, validated_data):
        validated_data['client'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        if data.get('budget_min') and data.get('budget_max'):
            if data['budget_min'] > data['budget_max']:
                raise serializers.ValidationError("Minimum budget cannot be greater than maximum budget.")
        
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError("Start date cannot be after end date.")
        
        return data


class ProjectStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('status', 'progress_percentage')

    def validate_status(self, value):
        current_status = self.instance.status if self.instance else None
        
        # Define valid status transitions
        valid_transitions = {
            'draft': ['published', 'cancelled'],
            'published': ['in_progress', 'cancelled'],
            'in_progress': ['completed', 'cancelled'],
            'completed': [],  # Cannot change from completed
            'cancelled': []   # Cannot change from cancelled
        }
        
        if current_status and value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot change status from {current_status} to {value}"
            )
        
        return value