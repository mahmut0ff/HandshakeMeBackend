from rest_framework import serializers
from apps.accounts.serializers import UserProfileSerializer
from .models import Category, Skill, ContractorProfile, Portfolio, PortfolioImage, Certification


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'icon', 'description', 'is_active')


class SkillSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Skill
        fields = ('id', 'name', 'category', 'category_name', 'is_active')


class PortfolioImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioImage
        fields = ('id', 'image', 'caption', 'is_primary', 'created_at')


class PortfolioSerializer(serializers.ModelSerializer):
    images = PortfolioImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Portfolio
        fields = (
            'id', 'title', 'description', 'category', 'category_name',
            'project_date', 'project_cost', 'client_name', 'is_featured',
            'images', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['contractor'] = self.context['contractor']
        return super().create(validated_data)


class CertificationSerializer(serializers.ModelSerializer):
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = Certification
        fields = (
            'id', 'name', 'issuing_organization', 'issue_date', 'expiry_date',
            'certificate_image', 'is_verified', 'is_expired', 'created_at'
        )
        read_only_fields = ('is_verified', 'created_at')

    def create(self, validated_data):
        validated_data['contractor'] = self.context['contractor']
        return super().create(validated_data)


class ContractorProfileSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    portfolio_items = PortfolioSerializer(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    average_hourly_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = ContractorProfile
        fields = (
            'id', 'user', 'business_name', 'license_number', 'insurance_verified',
            'experience_level', 'hourly_rate_min', 'hourly_rate_max', 'average_hourly_rate',
            'availability_status', 'response_time_hours', 'completed_projects',
            'rating_average', 'rating_count', 'service_radius',
            'categories', 'skills', 'portfolio_items', 'certifications',
            'created_at', 'updated_at'
        )
        read_only_fields = ('completed_projects', 'rating_average', 'rating_count', 'created_at', 'updated_at')


class ContractorProfileUpdateSerializer(serializers.ModelSerializer):
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    skill_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ContractorProfile
        fields = (
            'business_name', 'license_number', 'experience_level',
            'hourly_rate_min', 'hourly_rate_max', 'availability_status',
            'response_time_hours', 'service_radius', 'category_ids', 'skill_ids'
        )

    def update(self, instance, validated_data):
        category_ids = validated_data.pop('category_ids', None)
        skill_ids = validated_data.pop('skill_ids', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update categories
        if category_ids is not None:
            categories = Category.objects.filter(id__in=category_ids, is_active=True)
            instance.categories.set(categories)
        
        # Update skills
        if skill_ids is not None:
            skills = Skill.objects.filter(id__in=skill_ids, is_active=True)
            instance.skills.set(skills)
        
        return instance


class ContractorListSerializer(serializers.ModelSerializer):
    """Simplified serializer for contractor listings"""
    user = UserProfileSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    primary_portfolio_image = serializers.SerializerMethodField()
    distance = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = ContractorProfile
        fields = (
            'id', 'user', 'business_name', 'experience_level',
            'hourly_rate_min', 'hourly_rate_max', 'availability_status',
            'response_time_hours', 'completed_projects', 'rating_average',
            'rating_count', 'categories', 'primary_portfolio_image', 'distance'
        )

    def get_primary_portfolio_image(self, obj):
        """Get the primary image from the most recent portfolio item"""
        portfolio_item = obj.portfolio_items.filter(is_featured=True).first()
        if not portfolio_item:
            portfolio_item = obj.portfolio_items.first()
        
        if portfolio_item:
            primary_image = portfolio_item.images.filter(is_primary=True).first()
            if not primary_image:
                primary_image = portfolio_item.images.first()
            
            if primary_image:
                return {
                    'id': primary_image.id,
                    'image': primary_image.image.url,
                    'caption': primary_image.caption
                }
        return None