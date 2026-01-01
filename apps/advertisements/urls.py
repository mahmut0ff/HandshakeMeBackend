from django.urls import path
from . import views

app_name = 'advertisements'

urlpatterns = [
    path('', views.AdvertisementListView.as_view(), name='advertisement-list'),
    path('<int:ad_id>/impression/', views.track_impression, name='track-impression'),
    path('<int:ad_id>/click/', views.track_click, name='track-click'),
    path('categories/', views.AdCategoryListView.as_view(), name='category-list'),
]