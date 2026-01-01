from django.db.models import Q, Avg, Count, Case, When, Value, DecimalField
from django.core.cache import cache
from .models import ContractorProfile, Category, Skill
import math


class ContractorService:
    """Service class for contractor-related business logic"""
    
    @staticmethod
    def search_contractors(
        query=None, 
        categories=None, 
        skills=None,
        min_rating=None,
        max_hourly_rate=None,
        min_hourly_rate=None,
        availability_only=False,
        user_location=None,
        max_distance=None,
        experience_level=None,
        verified_only=False,
        limit=20,
        offset=0
    ):
        """
        Advanced contractor search with multiple filters
        """
        contractors = ContractorProfile.objects.select_related('user').prefetch_related(
            'categories', 'skills', 'portfolio_items__images'
        ).filter(user__is_active=True)
        
        # Text search
        if query:
            contractors = contractors.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(business_name__icontains=query) |
                Q(user__bio__icontains=query)
            )
        
        # Category filter
        if categories:
            contractors = contractors.filter(categories__id__in=categories).distinct()
        
        # Skills filter
        if skills:
            contractors = contractors.filter(skills__id__in=skills).distinct()
        
        # Rating filter
        if min_rating:
            contractors = contractors.filter(rating_average__gte=min_rating)
        
        # Hourly rate filters
        if min_hourly_rate:
            contractors = contractors.filter(hourly_rate_min__gte=min_hourly_rate)
        if max_hourly_rate:
            contractors = contractors.filter(hourly_rate_max__lte=max_hourly_rate)
        
        # Availability filter
        if availability_only:
            contractors = contractors.filter(availability_status=True)
        
        # Experience level filter
        if experience_level:
            contractors = contractors.filter(experience_level=experience_level)
        
        # Verified contractors only
        if verified_only:
            contractors = contractors.filter(user__is_verified=True)
        
        # Distance-based filtering (if user location is provided)
        if user_location and max_distance:
            # This would require PostGIS for proper implementation
            # For now, we'll use a simple approximation
            contractors = ContractorService._filter_by_distance(
                contractors, user_location, max_distance
            )
        
        # Order by rating and completed projects
        contractors = contractors.annotate(
            priority_score=Case(
                When(rating_average__gte=4.5, then=Value(3)),
                When(rating_average__gte=4.0, then=Value(2)),
                When(rating_average__gte=3.5, then=Value(1)),
                default=Value(0),
                output_field=DecimalField()
            )
        ).order_by('-priority_score', '-rating_average', '-completed_projects')
        
        return contractors[offset:offset + limit]
    
    @staticmethod
    def _filter_by_distance(contractors, user_location, max_distance):
        """
        Filter contractors by distance from user location
        This is a simplified implementation - in production, use PostGIS
        """
        filtered_contractors = []
        user_lat, user_lng = user_location
        
        for contractor in contractors:
            if contractor.user.location:
                # This would need proper geocoding in production
                # For now, assume location is stored as "lat,lng"
                try:
                    contractor_lat, contractor_lng = map(float, contractor.user.location.split(','))
                    distance = ContractorService._calculate_distance(
                        user_lat, user_lng, contractor_lat, contractor_lng
                    )
                    if distance <= max_distance:
                        contractor.distance = distance
                        filtered_contractors.append(contractor)
                except (ValueError, AttributeError):
                    continue
        
        return filtered_contractors
    
    @staticmethod
    def _calculate_distance(lat1, lng1, lat2, lng2):
        """
        Calculate distance between two points using Haversine formula
        Returns distance in miles
        """
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @staticmethod
    def get_contractor_stats():
        """Get cached contractor statistics"""
        cache_key = "contractor_stats"
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = {
                'total_contractors': ContractorProfile.objects.filter(user__is_active=True).count(),
                'verified_contractors': ContractorProfile.objects.filter(
                    user__is_active=True, user__is_verified=True
                ).count(),
                'available_contractors': ContractorProfile.objects.filter(
                    user__is_active=True, availability_status=True
                ).count(),
                'avg_rating': ContractorProfile.objects.filter(
                    user__is_active=True, rating_count__gt=0
                ).aggregate(avg_rating=Avg('rating_average'))['avg_rating'] or 0,
                'categories_count': Category.objects.filter(is_active=True).count(),
                'skills_count': Skill.objects.filter(is_active=True).count(),
            }
            cache.set(cache_key, stats, timeout=3600)  # Cache for 1 hour
        
        return stats
    
    @staticmethod
    def get_recommended_contractors(user, limit=10):
        """
        Get recommended contractors based on user's project history
        This is a simplified recommendation system
        """
        # In a real system, this would use machine learning algorithms
        # For now, we'll recommend based on popular categories and high ratings
        
        contractors = ContractorProfile.objects.select_related('user').prefetch_related(
            'categories', 'portfolio_items__images'
        ).filter(
            user__is_active=True,
            availability_status=True,
            rating_average__gte=4.0
        ).order_by('-rating_average', '-completed_projects')[:limit]
        
        return contractors
    
    @staticmethod
    def update_contractor_completion_stats(contractor_profile):
        """Update contractor's completion statistics"""
        contractor_profile.completed_projects += 1
        contractor_profile.save(update_fields=['completed_projects'])
        
        # Clear cache to refresh stats
        cache.delete("contractor_stats")