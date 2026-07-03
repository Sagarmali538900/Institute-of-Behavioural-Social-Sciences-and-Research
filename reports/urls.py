from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('assignments/', views.admin_assignments, name='admin_assignments'),
    path('assignments/edit/<int:assignment_id>/', views.edit_assignment, name='edit_assignment'),
    path('assignments/delete/<int:assignment_id>/', views.delete_assignment, name='delete_assignment'),
    path('results/', views.admin_results, name='admin_results'),
    path('results/<int:result_id>/', views.admin_result_detail, name='admin_result_detail'),
    path('email-logs/', views.admin_email_logs, name='admin_email_logs'),
    
    # Franchise Management (Owner-only)
    path('franchises/', views.admin_franchises, name='admin_franchises'),
    path('franchises/toggle/<int:user_id>/', views.toggle_franchise, name='toggle_franchise'),
    
    # Auth views
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
]
