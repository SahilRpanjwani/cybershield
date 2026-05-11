# teams/urls.py
from django.urls import path
from . import views

app_name = 'teams'

urlpatterns = [
    path('dashboard/', views.team_dashboard, name='team_dashboard'),
    path('<int:team_id>/tasks/create/', views.team_task_create, name='team_task_create'),
    path('task/<int:task_id>/assign/', views.assign_task, name='assign_task'),
    path('task/<int:task_id>/delete/', views.delete_task, name='delete_task'),
path('task/<int:task_id>/', views.task_detail, name='task_detail'),
]