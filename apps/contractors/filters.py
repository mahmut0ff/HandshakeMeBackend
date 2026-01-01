import django_filters
from .models import ContractorProfile, Category


class ContractorFilter(django_filters.FilterSet):
    categories = django_filters.ModelMultipleChoiceFilter(
        queryset=Category.objects.filter(is_active=True),
        field_name='categories',
        to_field_name='id'
    )
    min_rating = django_filters.NumberFilter(field_name='rating_average', lookup_expr='gte')
    max_hourly_rate = django_filters.NumberFilter(field_name='hourly_rate_max', lookup_expr='lte')
    min_hourly_rate = django_filters.NumberFilter(field_name='hourly_rate_min', lookup_expr='gte')
    availability_only = django_filters.BooleanFilter(field_name='availability_status')
    verified_only = django_filters.BooleanFilter(field_name='user__is_verified')
    experience_level = django_filters.ChoiceFilter(choices=ContractorProfile.EXPERIENCE_CHOICES)
    
    class Meta:
        model = ContractorProfile
        fields = [
            'categories', 'min_rating', 'max_hourly_rate', 'min_hourly_rate',
            'availability_only', 'verified_only', 'experience_level'
        ]