from django.urls import path
from resource_planning import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/<int:project_id>/gantt/', views.project_gantt, name='project_gantt'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:project_id>/tasks-api/', views.project_tasks_api, name='project_tasks_api'),
    path('projects/<int:project_id>/tasks-api/create/', views.task_create_api, name='task_create_api'),
    path('workload/', views.workload, name='workload'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/edit/', views.project_edit, name='project_edit'),
    path('team/', views.team, name='team'),
    path('team/add-employee/', views.add_employee, name='add_employee'),
    path('task/<int:task_id>/', views.task_detail, name='task_detail_view'),
    path('change-request/<int:request_id>/approve/', views.approve_executor_change, name='approve-change'),
    path('task/<int:task_id>/update-status/', views.update_task_status, name='update_task_status'),
    path('change-request/<int:request_id>/approve/', views.approve_executor_change, name='approve_change'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
]