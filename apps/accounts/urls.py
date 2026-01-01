from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile management
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/stats/', views.profile_stats_view, name='profile_stats'),
    path('profile/avatar/', views.avatar_upload_view, name='avatar_upload'),
    path('change-password/', views.change_password_view, name='change_password'),
    
    # Address management
    path('addresses/', views.AddressListCreateView.as_view(), name='address_list_create'),
    path('addresses/<int:pk>/', views.AddressDetailView.as_view(), name='address_detail'),
]