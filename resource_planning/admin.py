from django.contrib import admin
from .models import Project, ProjectStatus, Priority

admin.site.register(Project)
admin.site.register(ProjectStatus)
admin.site.register(Priority)