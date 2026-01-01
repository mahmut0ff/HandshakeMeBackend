from django.urls import path
from . import views

urlpatterns = [
    # Project CRUD
    path('', views.ProjectListCreateView.as_view(), name='project_list_create'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('<int:pk>/status/', views.ProjectStatusUpdateView.as_view(), name='project_status_update'),
    
    # Project applications
    path('<int:project_id>/apply/', views.ProjectApplicationCreateView.as_view(), name='project_apply'),
    path('<int:project_id>/applications/', views.ProjectApplicationListView.as_view(), name='project_applications'),
    path('applications/<int:pk>/accept/', views.AcceptApplicationView.as_view(), name='accept_application'),
    path('applications/<int:pk>/reject/', views.RejectApplicationView.as_view(), name='reject_application'),
    
    # Project images
    path('<int:project_id>/images/', views.ProjectImageUploadView.as_view(), name='project_image_upload'),
    
    # Project milestones
    path('<int:project_id>/milestones/', views.ProjectMilestoneListCreateView.as_view(), name='project_milestones'),
    path('milestones/<int:pk>/', views.ProjectMilestoneDetailView.as_view(), name='milestone_detail'),
    
    # Project updates
    path('<int:project_id>/updates/', views.ProjectUpdateListCreateView.as_view(), name='project_updates'),
    
    # Project documents
    path('<int:project_id>/documents/', views.ProjectDocumentListCreateView.as_view(), name='project_documents'),
    path('documents/<int:pk>/', views.ProjectDocumentDetailView.as_view(), name='document_detail'),
    
    # Statistics and recommendations
    path('stats/', views.project_stats_view, name='project_stats'),
    path('recommended/', views.recommended_projects_view, name='recommended_projects'),
]