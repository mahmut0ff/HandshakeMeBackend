from django.urls import path
from . import views

urlpatterns = [
    # Reviews
    path('', views.ReviewListCreateView.as_view(), name='review_list_create'),
    path('<int:pk>/', views.ReviewDetailView.as_view(), name='review_detail'),
    path('<int:pk>/response/', views.ReviewResponseCreateView.as_view(), name='review_response_create'),
    path('<int:pk>/helpful/', views.ReviewHelpfulView.as_view(), name='review_helpful'),
    
    # Review images
    path('<int:review_id>/images/', views.ReviewImageUploadView.as_view(), name='review_image_upload'),
    
    # Contractor reviews
    path('contractor/<int:contractor_id>/', views.ContractorReviewListView.as_view(), name='contractor_reviews'),
    
    # Statistics
    path('stats/', views.review_stats_view, name='review_stats'),
    path('contractor/<int:contractor_id>/stats/', views.contractor_review_stats_view, name='contractor_review_stats'),
]