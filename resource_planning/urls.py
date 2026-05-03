from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/<int:project_id>/gantt/', views.project_gantt, name='project_gantt'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:project_id>/tasks-api/', views.project_tasks_api, name='project_tasks_api'),
    path('projects/<int:project_id>/tasks-api/create/', views.task_create_api, name='task_create_api'),
    path('workload/', views.workload, name='workload'),
]