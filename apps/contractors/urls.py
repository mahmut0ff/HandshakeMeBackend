from django.urls import path
from . import views

urlpatterns = [
    # Categories and Skills
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('skills/', views.SkillListView.as_view(), name='skill_list'),
    
    # Contractor listings and details
    path('', views.ContractorListView.as_view(), name='contractor_list'),
    path('<int:pk>/', views.ContractorDetailView.as_view(), name='contractor_detail'),
    path('stats/', views.contractor_stats_view, name='contractor_stats'),
    path('recommended/', views.recommended_contractors_view, name='recommended_contractors'),
    
    # Contractor profile management
    path('profile/', views.ContractorProfileView.as_view(), name='contractor_profile'),
    
    # Portfolio management
    path('portfolio/', views.PortfolioListCreateView.as_view(), name='portfolio_list_create'),
    path('portfolio/<int:pk>/', views.PortfolioDetailView.as_view(), name='portfolio_detail'),
    path('portfolio/<int:portfolio_id>/images/', views.PortfolioImageUploadView.as_view(), name='portfolio_image_upload'),
    
    # Certification management
    path('certifications/', views.CertificationListCreateView.as_view(), name='certification_list_create'),
    path('certifications/<int:pk>/', views.CertificationDetailView.as_view(), name='certification_detail'),
]