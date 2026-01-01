from rest_framework import serializers
from django.db import models
from apps.accounts.serializers import UserProfileSerializer
from apps.contractors.serializers import ContractorListSerializer
from .models import Review, ReviewImage, ReviewResponse, ReviewHelpful


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ('id', 'image', 'caption', 'created_at')
        read_only_fields = ('created_at',)


class ReviewResponseSerializer(serializers.ModelSerializer):
    contractor_name = serializers.CharField(source='contractor.full_name', read_only=True)
    
    class Meta:
        model = ReviewResponse
        fields = ('id', 'contractor_name', 'response_text', 'created_at', 'updated_at')
        read_only_fields = ('contractor_name', 'created_at', 'updated_at')


class ReviewHelpfulSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewHelpful
        fields = ('is_helpful',)


class ReviewSerializer(serializers.ModelSerializer):
    client = UserProfileSerializer(read_only=True)
    contractor = ContractorListSerializer(read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    response = ReviewResponseSerializer(read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    helpful_count = serializers.SerializerMethodField()
    not_helpful_count = serializers.SerializerMethodField()
    user_helpful_vote = serializers.SerializerMethodField()
    average_category_rating = serializers.ReadOnlyField()
    
    class Meta:
        model = Review
        fields = (
            'id', 'client', 'contractor', 'project', 'project_title',
            'rating', 'quality_rating', 'communication_rating',
            'timeliness_rating', 'professionalism_rating',
            'title', 'comment', 'is_verified', 'is_featured', 'is_public',
            'images', 'response', 'helpful_count', 'not_helpful_count',
            'user_helpful_vote', 'average_category_rating',
            'created_at', 'updated_at'
        )
        read_only_fields = ('client', 'contractor', 'is_verified', 'created_at', 'updated_at')

    def get_helpful_count(self, obj):
        return obj.helpful_votes.filter(is_helpful=True).count()

    def get_not_helpful_count(self, obj):
        return obj.helpful_votes.filter(is_helpful=False).count()

    def get_user_helpful_vote(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            vote = obj.helpful_votes.filter(user=request.user).first()
            return vote.is_helpful if vote else None
        return None


class ReviewCreateSerializer(serializers.ModelSerializer):
    contractor_id = serializers.IntegerField(write_only=True)
    project_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Review
        fields = (
            'contractor_id', 'project_id', 'rating', 'quality_rating',
            'communication_rating', 'timeliness_rating', 'professionalism_rating',
            'title', 'comment', 'is_public'
        )

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

    def validate_contractor_id(self, value):
        from apps.contractors.models import ContractorProfile
        try:
            contractor = ContractorProfile.objects.get(id=value)
            return contractor
        except ContractorProfile.DoesNotExist:
            raise serializers.ValidationError("Contractor not found")

    def validate_project_id(self, value):
        if value:
            from apps.projects.models import Project
            try:
                project = Project.objects.get(id=value)
                return project
            except Project.DoesNotExist:
                raise serializers.ValidationError("Project not found")
        return None

    def validate(self, data):
        contractor = data.get('contractor_id')
        project = data.get('project_id')
        client = self.context['request'].user
        
        # Check if user already reviewed this contractor for this project
        existing_review = Review.objects.filter(
            client=client,
            contractor=contractor,
            project=project
        ).first()
        
        if existing_review:
            raise serializers.ValidationError(
                "You have already reviewed this contractor for this project"
            )
        
        # If project is specified, verify the user was the client
        if project and project.client != client:
            raise serializers.ValidationError(
                "You can only review contractors for your own projects"
            )
        
        return data

    def create(self, validated_data):
        contractor = validated_data.pop('contractor_id')
        project = validated_data.pop('project_id', None)
        
        review = Review.objects.create(
            client=self.context['request'].user,
            contractor=contractor,
            project=project,
            **validated_data
        )
        
        return review