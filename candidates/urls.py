from django.urls import path
from . import views

urlpatterns = [
    path('', views.exam_entry, name='exam_entry'),
    path('start/<int:session_id>/', views.exam_start, name='exam_start'),
    path('session/<int:session_id>/', views.exam_run, name='exam_run'),
    path('session/<int:session_id>/save-answers/', views.save_answers_ajax, name='save_answers_ajax'),
    path('session/<int:session_id>/submit-section/', views.submit_section_ajax, name='submit_section_ajax'),
    path('session/<int:session_id>/completed/', views.exam_completed, name='exam_completed'),
]
