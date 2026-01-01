import django_filters
from .models import Project
from apps.contractors.models import Category


class ProjectFilter(django_filters.FilterSet):
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.filter(is_active=True)
    )
    status = django_filters.MultipleChoiceFilter(
        choices=Project.STATUS_CHOICES
    )
    priority = django_filters.ChoiceFilter(
        choices=Project.PRIORITY_CHOICES
    )
    min_budget = django_filters.NumberFilter(field_name='budget_min', lookup_expr='gte')
    max_budget = django_filters.NumberFilter(field_name='budget_max', lookup_expr='lte')
    city = django_filters.CharFilter(lookup_expr='icontains')
    state = django_filters.CharFilter(lookup_expr='icontains')
    client = django_filters.NumberFilter(field_name='client__id')
    contractor = django_filters.NumberFilter(field_name='contractor__id')
    
    class Meta:
        model = Project
        fields = [
            'category', 'status', 'priority', 'min_budget', 'max_budget',
            'city', 'state', 'client', 'contractor'
        ]