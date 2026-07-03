from django.urls import path
from . import views

urlpatterns = [
    path('', views.exam_list, name='exam_list'),
    path('create/', views.exam_create, name='exam_create'),
    path('<int:exam_id>/', views.exam_detail, name='exam_detail'),
    path('<int:exam_id>/edit/', views.exam_edit, name='exam_edit'),
    path('<int:exam_id>/delete/', views.exam_delete, name='exam_delete'),
    
    # Section Management
    path('<int:exam_id>/section/add/', views.section_add, name='section_add'),
    path('section/<int:section_id>/edit/', views.section_edit, name='section_edit'),
    path('section/<int:section_id>/delete/', views.section_delete, name='section_delete'),
    
    # Question Management
    path('section/<int:section_id>/question/add/', views.question_add, name='question_add'),
    path('question/<int:question_id>/edit/', views.question_edit, name='question_edit'),
    path('question/<int:question_id>/delete/', views.question_delete, name='question_delete'),
    
    # Import/Export Management
    path('<int:exam_id>/export/json/', views.exam_export_json, name='exam_export_json'),
    path('<int:exam_id>/export/excel/', views.exam_export_excel, name='exam_export_excel'),
    path('import/', views.exam_import, name='exam_import'),
    path('<int:exam_id>/import/', views.exam_import, name='exam_import_overwrite'),
]
