from django.shortcuts import render
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import date
from .models import Project, TaskAssignment, KPI, ProjectStatus
from task_management.models import Task


def dashboard(request):
    # Ключевые метрики
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(status__name='Активен').count()
    completed_projects = Project.objects.filter(status__name='Завершён').count()

    # Просроченные задачи (дедлайн прошёл, задача не завершена)
    overdue_tasks = Task.objects.filter(
        planned_end_date__lt=timezone.now()
    ).exclude(status__name='Готово').count()

    # Средняя загрузка команды
    total_planned = TaskAssignment.objects.aggregate(total=Sum('planned_hours'))['total'] or 0
    total_actual = TaskAssignment.objects.aggregate(total=Sum('actual_hours'))['total'] or 0
    avg_utilization = round((total_actual / total_planned * 100)) if total_planned > 0 else 0

    # Данные для графика "Прогресс проектов"
    projects = Project.objects.all()[:5]
    project_names = [p.name for p in projects]
    project_progress = []
    for p in projects:
        kpi = KPI.objects.filter(project=p, name='Процент выполнения').first()
        project_progress.append(float(kpi.value) if kpi else 0)

    # Данные для графика "Статусы задач"
    task_statuses = Task.objects.values('status__name').annotate(count=Count('id'))
    status_labels = [ts['status__name'] for ts in task_statuses]
    status_counts = [ts['count'] for ts in task_statuses]

    # Таблица проектов
    project_list = Project.objects.select_related('status', 'priority', 'manager').all()[:10]

    # KPI для отображения
    kpi_list = KPI.objects.select_related('project').all()[:10]

    context = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'overdue_tasks': overdue_tasks,
        'avg_utilization': avg_utilization,
        'project_names': project_names,
        'project_progress': project_progress,
        'status_labels': status_labels,
        'status_counts': status_counts,
        'project_list': project_list,
        'kpi_list': kpi_list,
    }
    return render(request, 'resource_planning/dashboard.html', context)



def project_list(request):
    # Получаем параметр фильтра из URL (?status=Активен)
    status_filter = request.GET.get('status', '')

    projects = Project.objects.select_related('status', 'priority', 'manager').all()

    if status_filter:
        projects = projects.filter(status__name=status_filter)

    # Получаем все статусы для выпадающего списка фильтра
    statuses = ProjectStatus.objects.all()

    # Подтягиваем KPI "Процент выполнения" для каждого проекта
    for project in projects:
        kpi = project.kpis.filter(name='Процент выполнения').first()
        project.progress = int(kpi.value) if kpi else 0

    context = {
        'projects': projects,
        'statuses': statuses,
        'current_filter': status_filter,
    }
    return render(request, 'resource_planning/project_list.html', context)

def project_gantt(request, project_id):
    project = Project.objects.get(id=project_id)
    return render(request, 'resource_planning/project_gantt.html', {'project': project})