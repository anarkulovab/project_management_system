from django.urls import path
from . import views

urlpatterns = [
    path('board/', views.kanban_board, name='kanban-board'),
    path('task/<int:task_id>/update-status/', views.update_task_status, name='update-task-status'),
    path('task/<int:task_id>/', views.task_detail, name='task-detail'),
    path('task/<int:task_id>/comment/', views.add_comment, name='add-comment'),
    path('task/create/', views.create_task, name='create-task'),
    path('dashboard/', views.personal_dashboard, name='personal-dashboard'),
    path('project/<int:project_id>/', views.project_detail, name='project-detail'),
    path('projects/', views.project_list, name='project-list'),
    path('task/<int:parent_task_id>/subtask/', views.create_subtask, name='create-subtask'),
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark-read'),
    path('notifications/read-all/', views.mark_all_read, name='mark-all-read'),
    path('task/<int:task_id>/request-change/', views.request_executor_change, name='request-change'),
    path('change-password/', views.change_password, name='change-password'),
    path('change-username/', views.change_username, name='change-username'),
]