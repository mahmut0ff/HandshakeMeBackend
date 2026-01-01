from rest_framework import serializers
from .models import Advertisement, AdCategory


class AdvertisementSerializer(serializers.ModelSerializer):
    click_through_rate = serializers.ReadOnlyField()
    is_currently_active = serializers.ReadOnlyField()

    class Meta:
        model = Advertisement
        fields = [
            'id', 'title', 'description', 'image', 'link_url', 'button_text',
            'ad_type', 'position', 'target_audience', 'background_color', 'text_color',
            'start_date', 'end_date', 'priority', 'is_active',
            'impressions', 'clicks', 'click_through_rate', 'is_currently_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['impressions', 'clicks', 'created_at', 'updated_at']


class AdCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdCategory
        fields = ['id', 'name', 'description', 'is_active', 'created_at']