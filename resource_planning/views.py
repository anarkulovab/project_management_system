from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User, Group
from django.shortcuts import redirect
from .models import Project, TaskAssignment, KPI, ProjectStatus, UserAbsence, Priority, Employee
from task_management.models import Task, TaskStatus
from .forms import ProjectForm
import json
from datetime import date, timedelta
from django.db import models
from django.contrib import messages
import random
import string

@login_required
# Дашборды
def dashboard(request):
    # Только проекты текущего руководителя
    projects = Project.objects.filter(manager=request.user)

    total_projects = projects.count()
    active_projects = projects.filter(status__name='Активен').count()
    completed_projects = projects.filter(status__name='Завершён').count()

    # Просроченные задачи только по проектам руководителя
    overdue_tasks = Task.objects.filter(
        project__manager=request.user,
        planned_end_date__lt=timezone.now()
    ).exclude(status__name='Готово').count()

    # Загрузка — только по задачам проектов руководителя
    assignments = TaskAssignment.objects.filter(task__project__manager=request.user)
    total_planned = assignments.aggregate(total=models.Sum('planned_hours'))['total'] or 0
    total_actual = assignments.aggregate(total=models.Sum('actual_hours'))['total'] or 0
    avg_utilization = round((total_actual / total_planned * 100)) if total_planned > 0 else 0

    # Данные для графиков
    project_names = [p.name for p in projects[:5]]
    project_progress = []
    for p in projects[:5]:
        kpi = KPI.objects.filter(project=p, name='Процент выполнения').first()
        project_progress.append(float(kpi.value) if kpi else 0)

    # Статусы задач — только по проектам руководителя
    task_statuses = Task.objects.filter(
        project__manager=request.user
    ).values('status__name').annotate(count=models.Count('id'))
    status_labels = [ts['status__name'] for ts in task_statuses]
    status_counts = [ts['count'] for ts in task_statuses]

    # Таблица проектов
    project_list = projects[:10]
    kpi_list = KPI.objects.filter(project__manager=request.user)[:20]

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


@login_required
def project_list(request):
    status_filter = request.GET.get('status', '')

    # Только проекты текущего руководителя
    projects = Project.objects.select_related('status', 'priority', 'manager').filter(manager=request.user)

    if status_filter:
        projects = projects.filter(status__name=status_filter)

    statuses = ProjectStatus.objects.all()
    priorities = Priority.objects.all()
    users = User.objects.filter(is_active=True, is_superuser=False)

    for project in projects:
        kpi = project.kpis.filter(name='Процент выполнения').first()
        project.progress = int(kpi.value) if kpi else 0

    context = {
        'projects': projects,
        'statuses': statuses,
        'priorities': priorities,
        'users': users,
        'current_filter': status_filter,
    }
    return render(request, 'resource_planning/project_list.html', context)

@login_required
# Создание проекта
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            default_status = ProjectStatus.objects.get(name='Активен')
            project.status = default_status
            project.manager = request.user
            project.save()
            form.save_m2m()  # сохраняет связи ManyToMany (participants)
            return redirect('project_detail', project_id=project.id)
    else:
        return redirect('project_list')

@login_required
# Диаграмма Ганта
def project_gantt(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    users = User.objects.filter(is_active=True, is_superuser=False)
    return render(request, 'resource_planning/project_gantt.html', {
        'project': project,
        'users': users,
    })

@login_required
# Задачи проекта
def project_tasks_api(request, project_id):
    tasks = Task.objects.filter(project_id=project_id).select_related('status', 'assigned_to')
    events = []
    for task in tasks:
        start = task.planned_start_date if hasattr(task, 'planned_start_date') and task.planned_start_date else task.created_at
        events.append({
            'id': task.id,
            'title': task.title,
            'start': start.isoformat(),
            'end': task.planned_end_date.isoformat() if task.planned_end_date else None,
            'color': get_status_color(task.status.name if task.status else ''),
            'extendedProps': {
                'status': task.status.name if task.status else 'Без статуса',
                'assignee': task.assigned_to.get_full_name() if task.assigned_to else 'Не назначен',
                'priority': task.priority,
            }
        })
    return JsonResponse(events, safe=False)


def get_status_color(status_name):
    """Возвращает цвет задачи в зависимости от статуса."""
    colors = {
        'Новая': '#3498DB',
        'В работе': '#F39C12',
        'На проверке': '#1ABC9C',
        'Готово': '#27AE60',
        'Заблокирована': '#E74C3C',
    }
    return colors.get(status_name, '#7F8C8D')


# Создание задач
from datetime import datetime

@login_required
@csrf_exempt
def task_create_api(request, project_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Некорректный JSON'}, status=400)

    title = data.get('title', 'Без названия')
    start_str = data.get('start')
    end_str = data.get('end')

    project = get_object_or_404(Project, id=project_id)
    default_status = TaskStatus.objects.filter(name='Новая').first()

    start_date = datetime.fromisoformat(start_str) if start_str else None
    end_date = datetime.fromisoformat(end_str) if end_str else None

    task = Task.objects.create(
        title=title,
        project=project,
        status=default_status,
        priority=data.get('priority', 'medium'),
        planned_start_date=start_date,
        planned_end_date=end_date,
        author=request.user,
    )

    assignee_id = data.get('assignee_id')
    if assignee_id:
        try:
            assignee = User.objects.get(id=assignee_id)
            task.assigned_to = assignee
            task.save()

            # Создаём назначение для расчёта загрузки
            TaskAssignment.objects.create(
                task=task,
                user=assignee,
                planned_hours=data.get('planned_hours', 0),
            )
        except User.DoesNotExist:
            pass

    return JsonResponse({
        'id': task.id,
        'title': task.title,
        'start': task.planned_start_date.isoformat() if task.planned_start_date else task.created_at.isoformat(),
        'end': task.planned_end_date.isoformat() if task.planned_end_date else None,
        'color': '#3498DB',
        'extendedProps': {
            'status': task.status.name if task.status else 'Новая',
            'assignee': task.assigned_to.get_full_name() if task.assigned_to else 'Не назначен',
            'priority': task.priority,
        }
    }, status=201)

@login_required
def workload(request):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    offset = int(request.GET.get('week_offset', 0))
    if offset != 0:
        week_start = week_start + timedelta(weeks=offset)
        week_end = week_end + timedelta(weeks=offset)

    # Фильтр по проекту
    project_id = request.GET.get('project_id', '')
    selected_project = None
    if project_id:
        selected_project = get_object_or_404(Project, id=project_id)
        users = User.objects.filter(participating_projects=selected_project).distinct()
    else:
        employees = Employee.objects.filter(manager=request.user).values_list('employee', flat=True)
        users = User.objects.filter(id__in=employees)

    workload_data = []
    total_planned = 0
    total_actual = 0

    for user in users:
        assignments = TaskAssignment.objects.filter(
            user=user,
            task__planned_end_date__gte=week_start,
            task__planned_end_date__lte=week_end
        )
        if project_id:
            assignments = assignments.filter(task__project_id=project_id)

        planned = assignments.aggregate(total=models.Sum('planned_hours'))['total'] or 0
        actual = assignments.aggregate(total=models.Sum('actual_hours'))['total'] or 0

        available = 40
        absences = UserAbsence.objects.filter(
            user=user,
            start_date__lte=week_end,
            end_date__gte=week_start
        )
        for absence in absences:
            absence_start = max(absence.start_date, week_start)
            absence_end = min(absence.end_date, week_end)
            days_absent = (absence_end - absence_start).days + 1
            available -= days_absent * 8

        if available > 0:
            load_percent = int((planned / available) * 100)
        else:
            load_percent = 0

        total_planned += planned
        total_actual += actual

        if load_percent > 100:
            load_class = 'danger'
        elif load_percent >= 80:
            load_class = 'warning'
        else:
            load_class = 'success'

        workload_data.append({
            'user': user,
            'planned': planned,
            'actual': actual,
            'available': available,
            'load_percent': load_percent,
            'load_class': load_class,
        })

    avg_load = int(total_planned / (len(users) * 40) * 100) if users else 0

    # Список проектов для фильтра
    projects = Project.objects.filter(manager=request.user) if request.user.is_authenticated else Project.objects.all()

    context = {
        'workload_data': workload_data,
        'week_start': week_start,
        'week_end': week_end,
        'offset': offset,
        'avg_load': avg_load,
        'projects': projects,
        'selected_project': selected_project,
    }
    return render(request, 'resource_planning/workload.html', context)

@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    tasks = Task.objects.filter(project=project).select_related('status', 'assigned_to', 'author')
    participants = project.participants.all()
    kpis = KPI.objects.filter(project=project)

    context = {
        'project': project,
        'tasks': tasks,
        'participants': participants,
        'kpis': kpis,
    }
    return render(request, 'resource_planning/project_detail.html', context)

@login_required
def project_edit(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)

    priorities = Priority.objects.all()
    users = User.objects.filter(is_active=True, is_superuser=False)

    context = {
        'form': form,
        'project': project,
        'priorities': priorities,
        'users': users,
    }
    return render(request, 'resource_planning/project_edit.html', context)

@login_required
def team(request):
    """Страница команды руководителя."""
    employees = Employee.objects.filter(manager=request.user).select_related('employee')
    context = {
        'employees': employees,
    }
    return render(request, 'resource_planning/team.html', context)


@login_required
def add_employee(request):
    """Добавление нового сотрудника в команду."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        if not email:
            messages.error(request, 'Email обязателен')
            return redirect('team')

        # Проверяем, существует ли пользователь с таким email
        user = User.objects.filter(email=email).first()

        if user:
            # Пользователь уже существует — проверяем, не добавлен ли уже
            if Employee.objects.filter(manager=request.user, employee=user).exists():
                messages.warning(request, f'{user.get_full_name() or user.username} уже в вашей команде')
            else:
                Employee.objects.create(manager=request.user, employee=user)
                messages.success(request, f'{user.get_full_name() or user.username} добавлен в команду')
        else:
            # Создаём нового пользователя
            username = email.split('@')[0]
            # Проверяем уникальность логина
            if User.objects.filter(username=username).exists():
                username = f"{username}{random.randint(100, 999)}"

            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            executor_group = Group.objects.get(name='Исполнитель')
            user.groups.add(executor_group)
            Employee.objects.create(manager=request.user, employee=user)
            messages.success(
                request,
                f'Сотрудник создан. Логин: {username}, Пароль: {password}. Передайте эти данные сотруднику.'
            )

        return redirect('team')

    return redirect('team')


def redirect_by_role(request):
    user = request.user
    if user.groups.filter(name='Руководитель проекта').exists():
        return redirect('dashboard')
    elif user.groups.filter(name='Исполнитель').exists():
        return redirect('/tasks/board')
    elif user.groups.filter(name='Директор').exists():
        return redirect('/tasks/')  # позже — десктоп Насти

    return redirect('dashboard')