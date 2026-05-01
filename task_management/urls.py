from django.urls import path
from . import views

urlpatterns = [
    path('board/', views.kanban_board, name='kanban-board'),
    path('task/<int:task_id>/update-status/', views.update_task_status, name='update-task-status'),
]