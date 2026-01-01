from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Address


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password', 'password_confirm', 'user_type', 'phone_number')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include email and password.')
        
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    skills = serializers.JSONField(default=list, required=False)
    hourly_rate = serializers.CharField(max_length=50, required=False, allow_blank=True)
    experience_years = serializers.IntegerField(default=0, required=False)
    is_contractor = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'phone_number', 'user_type', 'avatar', 'bio', 'location',
            'is_verified', 'is_online', 'last_seen', 'created_at',
            'skills', 'hourly_rate', 'experience_years', 'is_contractor'
        )
        read_only_fields = ('id', 'email', 'is_verified', 'is_online', 'last_seen', 'created_at')
    
    def get_is_contractor(self, obj):
        return obj.user_type == 'contractor'


class UserUpdateSerializer(serializers.ModelSerializer):
    skills = serializers.JSONField(default=list, required=False)
    hourly_rate = serializers.CharField(max_length=50, required=False, allow_blank=True)
    experience_years = serializers.IntegerField(default=0, required=False)
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number', 'avatar', 'bio', 'location', 'user_type', 'skills', 'hourly_rate', 'experience_years')


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            'id', 'title', 'street_address', 'city', 'state', 'postal_code',
            'country', 'latitude', 'longitude', 'is_default', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)