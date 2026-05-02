from django.contrib import admin
from .models import (
    Role, ProjectStatus, Priority, AbsenceType,
    ProbabilityLevel, ImpactLevel, RiskStatus,
    Project, TaskAssignment, UserAbsence,
    Risk, RiskHistory, Budget, KPI
)

admin.site.register(Role)
admin.site.register(ProjectStatus)
admin.site.register(Priority)
admin.site.register(AbsenceType)
admin.site.register(ProbabilityLevel)
admin.site.register(ImpactLevel)
admin.site.register(RiskStatus)
admin.site.register(Project)
admin.site.register(TaskAssignment)
admin.site.register(UserAbsence)
admin.site.register(Risk)
admin.site.register(RiskHistory)
admin.site.register(Budget)
admin.site.register(KPI)