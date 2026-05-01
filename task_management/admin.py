# task_management/admin.py

from django.contrib import admin
from .models import TaskStatus, Task, Comment, TaskHistory

admin.site.register(TaskStatus)
admin.site.register(Task)
admin.site.register(Comment)
admin.site.register(TaskHistory)