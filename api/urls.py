from django.urls import path
from . import views

urlpatterns = [
    path('projects/', views.ProjectListView.as_view(), name='api_projects'),
    path('projects/<int:project_id>/', views.ProjectDetailView.as_view(), name='api_project_detail'),
    path('budgets/', views.BudgetListView.as_view(), name='api_budgets'),
    path('risks/', views.RiskListView.as_view(), name='api_risks'),
    path('risks/<int:risk_id>/', views.RiskUpdateView.as_view(), name='api_risk_update'),
    path('risks/<int:risk_id>/history/', views.RiskHistoryView.as_view(), name='api_risk_history'),
    path('team/', views.TeamView.as_view(), name='api_team'),
    path('audit/', views.AuditLogView.as_view(), name='api_audit'),
    path('users/<int:user_id>/', views.UserDeleteView.as_view(), name='api_user_delete'),
    path('users/<int:user_id>/transfer/', views.UserTransferView.as_view(), name='api_user_transfer'),
    path('kpi/', views.KPIListView.as_view(), name='api_kpi'),
    path('projects/<int:project_id>/tasks/', views.ProjectTasksView.as_view(), name='api_project_tasks'),
    path('desktop-login/', views.DesktopLoginView.as_view(), name='api_desktop_login'),
]