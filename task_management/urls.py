from django.urls import path
from . import views

urlpatterns = [
    path('board/', views.kanban_board, name='kanban-board'),
    path('task/<int:task_id>/update-status/', views.update_task_status, name='update-task-status'),
    path('task/<int:task_id>/', views.task_detail, name='task-detail'),
    path('task/<int:task_id>/comment/', views.add_comment, name='add-comment'),
]