from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User, Group
from django.shortcuts import redirect
from .models import Project, TaskAssignment, KPI, ProjectStatus, UserAbsence, Priority, Employee, AbsenceType
from task_management.models import Task, TaskStatus, Notification
from .forms import ProjectForm
import json
from datetime import date, timedelta
from django.db import models
from django.contrib import messages
import random
import string
from task_management.models import ExecutorChangeRequest

@login_required
def dashboard(request):
    """Функция для вывода дашборда"""
    # Только проекты текущего руководителя
    projects = Project.objects.filter(manager=request.user)
    total_projects = projects.count()
    active_projects = projects.filter(status__name='Активен').count()
    completed_projects = projects.filter(status__name='Завершён').count()

    # Просроченные задачи только по проектам руководителя
    overdue_tasks = Task.objects.filter(project__manager=request.user, planned_end_date__lt=timezone.now()).exclude(status__name='Готово').count()

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

    # Статусы задач: выводятся только по проектам руководителя
    task_statuses = Task.objects.filter(project__manager=request.user).values('status__name').annotate(count=models.Count('id'))
    status_labels = [ts['status__name'] for ts in task_statuses]
    status_counts = [ts['count'] for ts in task_statuses]

    # Таблица проектов
    project_list = projects[:10]
    kpi_list = KPI.objects.filter(project__manager=request.user)[:20]

    context = {
        'total_projects': total_projects, 'active_projects': active_projects, 'completed_projects': completed_projects, 'overdue_tasks': overdue_tasks,
        'avg_utilization': avg_utilization, 'project_names': project_names, 'project_progress': project_progress, 'status_labels': status_labels,
        'status_counts': status_counts, 'project_list': project_list, 'kpi_list': kpi_list,}
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
    employee_ids = Employee.objects.filter(manager=request.user).values_list('employee_id', flat=True)
    users = User.objects.filter(id__in=employee_ids)

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
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, user=request.user)
        if form.is_valid():
            project = form.save(commit=False)

            # Проверка дат
            if project.start_date_plan and project.end_date_plan:
                if project.start_date_plan > project.end_date_plan:
                    messages.error(request, 'Дата начала не может быть позже даты окончания.')
                    return redirect(request.META.get('HTTP_REFERER', 'project_list'))

            default_status = ProjectStatus.objects.get(name='Активен')
            project.status = default_status
            project.manager = request.user
            project.save()
            form.save_m2m()
            # for participant in project.participants.all():
            #     Notification.objects.create(
            #         user=participant,
            #         task=None,
            #         message=f'{request.user.get_full_name() or request.user.username} добавил вас в проект «{project.name}».'
            #     )

            return redirect('project_detail', project_id=project.id)
        else:
            messages.error(request, 'Проверьте правильность заполнения полей.')
            return redirect(request.META.get('HTTP_REFERER', 'project_list'))

    return redirect('project_list')

@login_required
# Диаграмма Ганта
def project_gantt(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    employee_ids = Employee.objects.filter(manager=request.user).values_list('employee_id', flat=True)
    users = User.objects.filter(id__in=employee_ids)
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

@csrf_exempt
@login_required
def task_create_api(request, project_id):
    """API для создания задачи через FullCalendar."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Некорректный JSON'}, status=400)

    title = data.get('title', 'Без названия')
    start_str = data.get('start')
    end_str = data.get('end')
    description = data.get('description', '')
    # Если плановые часы не указаны — считаем по дням
    planned_hours = data.get('planned_hours')
    project = get_object_or_404(Project, id=project_id)

    # Преобразуем строки в datetime
    start_date = datetime.fromisoformat(start_str) if start_str else None
    end_date = datetime.fromisoformat(end_str) if end_str else None

    if planned_hours:
        planned_hours = int(planned_hours)
    elif start_date and end_date:
        work_days = max(1, (end_date - start_date).days + 1)
        planned_hours = work_days * 8
    else:
        planned_hours = 0

    # Проверка: плановые часы не могут превышать доступное время
    if start_date and end_date and planned_hours > 0:
        work_days = max(1, (end_date - start_date).days + 1)
        max_hours = work_days * 8
        if planned_hours > max_hours:
            return JsonResponse({
                'error': f'Плановые часы ({planned_hours} ч) превышают доступное время за период ({max_hours} ч за {work_days} дн.).'
            }, status=400)
    # Проверка: нельзя создать задачу с прошедшей датой начала
    if start_date and start_date.date() < date.today():
        return JsonResponse({'error': 'Нельзя создать задачу с прошедшей датой начала'}, status=400)

    # Определяем статус
    if start_date and start_date.date() > date.today():
        default_status = TaskStatus.objects.filter(name='Запланирована').first()
    else:
        default_status = TaskStatus.objects.filter(name='Новая').first()

    # Получаем исполнителя ДО проверок
    assignee_id = data.get('assignee_id')
    assignee = None
    if assignee_id:
        try:
            assignee = User.objects.get(id=int(assignee_id))
        except (User.DoesNotExist, ValueError):
            pass

    # Проверка на отсутствие
    if assignee and start_date and end_date:
        overlapping = UserAbsence.objects.filter(
            user=assignee,
            start_date__lte=end_date.date(),
            end_date__gte=start_date.date()
        )
        if overlapping.exists():
            return JsonResponse({
                'error': f'Нельзя назначить задачу: у {assignee.get_full_name() or assignee.username} запланировано отсутствие в этом периоде.'
            }, status=400)

    # Создаём задачу
    task = Task.objects.create(
        title=title,
        description=description,
        project=project,
        status=default_status,
        priority=data.get('priority', 'medium'),
        planned_start_date=start_date,
        planned_end_date=end_date,
        author=request.user,
    )

    if assignee:
        task.assigned_to = assignee
        task.save()

    if assignee and planned_hours > 0:
        TaskAssignment.objects.create(
            task=task,
            user=assignee,
            planned_hours=planned_hours,
        )

    # Проверка загрузки
    warning_msg = None
    if assignee and planned_hours > 0:
        base_date = start_date if start_date else timezone.now()
        week_start = base_date - timedelta(days=base_date.weekday())
        week_end = week_start + timedelta(days=6)

        emp_rel = Employee.objects.filter(manager=request.user, employee=assignee).first()
        weekly_norm = emp_rel.weekly_work_hours if emp_rel else 40

        current_load = TaskAssignment.objects.filter(
            user=assignee,
            task__planned_end_date__gte=week_start,
            task__planned_end_date__lte=week_end
        ).exclude(task=task).aggregate(total=models.Sum('planned_hours'))['total'] or 0

        new_total = current_load + planned_hours

        if new_total > weekly_norm:
            warning_msg = (
                f'Внимание: загрузка {assignee.get_full_name() or assignee.username} '
                f'на неделе {week_start.strftime("%d.%m")}–{week_end.strftime("%d.%m")} '
                f'составит {new_total} ч при норме {weekly_norm} ч.'
            )

    # Уведомление
    if assignee:
        Notification.objects.create(
            user=assignee,
            task=task,
            message=f'{request.user.get_full_name() or request.user.username} назначил вам задачу «{task.title}» в проекте «{project.name}».'
        )

    # Цвет задачи
    status_name = task.status.name if task.status else 'Новая'
    if status_name == 'Запланирована':
        task_color = '#b0b0b0'
    elif warning_msg:
        task_color = '#f0b065'
    else:
        task_color = '#3498DB'

    response_data = {
        'id': task.id,
        'title': task.title,
        'start': task.planned_start_date.isoformat() if task.planned_start_date else task.created_at.isoformat(),
        'end': task.planned_end_date.isoformat() if task.planned_end_date else None,
        'color': task_color,
        'extendedProps': {
            'status': status_name,
            'assignee': task.assigned_to.get_full_name() if task.assigned_to else 'Не назначен',
            'priority': task.priority,
        }
    }

    if warning_msg:
        response_data['warning'] = warning_msg

    return JsonResponse(response_data, status=201)

@login_required
def workload(request):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    offset = int(request.GET.get('week_offset', 0))
    if offset != 0:
        week_start = week_start + timedelta(weeks=offset)
        week_end = week_end + timedelta(weeks=offset)

    project_id = request.GET.get('project_id', '')
    selected_project = None
    if project_id:
        selected_project = get_object_or_404(Project, id=project_id)

    # Получаем сотрудников руководителя
    employee_ids = Employee.objects.filter(manager=request.user).values_list('employee_id', flat=True)
    users = User.objects.filter(id__in=employee_ids)

    # Общая статистика за весь период
    total_data = []
    grand_planned = 0
    grand_actual = 0

    for user in users:
        emp_rel = Employee.objects.get(manager=request.user, employee=user)
        weekly_norm = emp_rel.weekly_work_hours

        # Все назначения сотрудника
        assignments = TaskAssignment.objects.filter(user=user)
        if project_id:
            assignments = assignments.filter(task__project_id=project_id)

        total_planned = assignments.aggregate(total=models.Sum('planned_hours'))['total'] or 0
        total_actual = assignments.aggregate(total=models.Sum('actual_hours'))['total'] or 0

        # Определяем временной диапазон: от самой ранней задачи до самой поздней
        task_dates = Task.objects.filter(
            assignments__user=user
        ).aggregate(
            min_date=models.Min('planned_start_date'),
            max_date=models.Max('planned_end_date')
        )
        min_date = task_dates['min_date']
        max_date = task_dates['max_date']

        if min_date and max_date and min_date != max_date:
            total_weeks = ((max_date - min_date).days // 7) + 1
        else:
            total_weeks = 1

        available_total = weekly_norm * total_weeks
        load_percent_total = int((total_planned / available_total) * 100) if available_total > 0 else 0

        if load_percent_total > 100:
            load_class = 'danger'
        elif load_percent_total >= 80:
            load_class = 'warning'
        else:
            load_class = 'success'

        grand_planned += total_planned
        grand_actual += total_actual

        total_data.append({
            'user': user,
            'planned': total_planned,
            'actual': total_actual,
            'available': available_total,
            'load_percent': load_percent_total,
            'load_class': load_class,
            'weeks': total_weeks,
            'weekly_norm': weekly_norm,
        })

    # Понедельная детализация
    weekly_data = []
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

        emp_rel = Employee.objects.get(manager=request.user, employee=user)
        available = emp_rel.weekly_work_hours

        absences = UserAbsence.objects.filter(
            user=user, start_date__lte=week_end, end_date__gte=week_start
        )

        absence_note = None
        if absences.exists():
            notes = []
            for a in absences:
                absence_start = max(a.start_date, week_start)
                absence_end = min(a.end_date, week_end)
                days_absent = (absence_end - absence_start).days + 1
                available -= days_absent * 8
                notes.append(f'{a.absence_type.name}: {a.start_date.strftime("%d.%m")}–{a.end_date.strftime("%d.%m")}')
            absence_note = '; '.join(notes)

        if available > 0:
            load_percent = int((planned / available) * 100)
        else:
            load_percent = 0

        if load_percent > 100:
            w_class = 'danger'
        elif load_percent >= 80:
            w_class = 'warning'
        else:
            w_class = 'success'

        weekly_data.append({
            'user': user,
            'planned': planned,
            'actual': actual,
            'available': available,
            'load_percent': load_percent,
            'load_class': w_class,
            'absence_note': absence_note,
        })

    projects = Project.objects.filter(manager=request.user)

    context = {
        'total_data': total_data,
        'weekly_data': weekly_data,
        'week_start': week_start,
        'week_end': week_end,
        'offset': offset,
        'grand_planned': grand_planned,
        'grand_actual': grand_actual,
        'projects': projects,
        'selected_project': selected_project,
    }
    return render(request, 'resource_planning/workload.html', context)

@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    tasks = Task.objects.filter(project=project).select_related('status', 'assigned_to', 'author')
    participants = project.participants.all()

    total_tasks = Task.objects.filter(project=project).count()
    completed_tasks = Task.objects.filter(project=project, status__name='Готово').count()
    overdue_tasks = Task.objects.filter(
        project=project,
        planned_end_date__lt=timezone.now()
    ).exclude(status__name='Готово').count()

    progress = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
    overdue_rate = int((overdue_tasks / total_tasks * 100)) if total_tasks > 0 else 0

    # Расчёт утилизации ресурсов
    participants = project.participants.all()
    total_utilization = 0
    if participants:
        for user in participants:
            assignments = TaskAssignment.objects.filter(user=user, task__project=project)
            planned = assignments.aggregate(total=models.Sum('planned_hours'))['total'] or 0
            actual = assignments.aggregate(total=models.Sum('actual_hours'))['total'] or 0
            if planned > 0:
                total_utilization += int((actual / planned * 100))
        avg_utilization = int(total_utilization / participants.count())
    else:
        avg_utilization = 0

    # Собираем KPI в список для шаблона
    kpis = [
        {'name': 'Процент выполнения', 'value': progress},
        {'name': 'Индекс соблюдения сроков', 'value': 100 - overdue_rate},
        {'name': 'Использование ресурсов', 'value': avg_utilization},
        {'name': 'Доля просроченных задач', 'value': overdue_rate},
    ]
    today_start = datetime.combine(date.today(), datetime.min.time())
    if not KPI.objects.filter(project=project, calculated_at__gte=today_start).exists():
        for kpi_item in kpis:
            KPI.objects.create(
                project=project,
                name=kpi_item['name'],
                value=kpi_item['value']
            )

    # Расчёт средней загрузки команды проекта
    participants = project.participants.all()
    total_load = 0
    participant_count = participants.count()
    if participant_count > 0:
        for user in participants:
            emp_rel = Employee.objects.filter(manager=request.user, employee=user).first()
            weekly_norm = emp_rel.weekly_work_hours if emp_rel else 40
            assignments = TaskAssignment.objects.filter(user=user, task__project=project)
            total_planned = assignments.aggregate(total=models.Sum('planned_hours'))['total'] or 0
            total_load += float(total_planned / weekly_norm * 100) if weekly_norm > 0 else 0
        avg_load = int(total_load / participant_count)
    else:
        avg_load = 0

    context = {
        'project': project,
        'tasks': tasks,
        'participants': participants,
        'kpis': kpis,
        'avg_load': avg_load,
    }
    return render(request, 'resource_planning/project_detail.html', context)


@login_required
def project_edit(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project, user=request.user)
        if form.is_valid():
            updated_project = form.save(commit=False)

            # Проверка: дата окончания не раньше даты начала
            if updated_project.start_date_plan and updated_project.end_date_plan:
                if updated_project.start_date_plan > updated_project.end_date_plan:
                    messages.error(request, 'Плановая дата окончания не может быть раньше даты начала.')
                    return redirect('project_edit', project_id=project.id)

            # Проверка: фактические даты не могут быть в будущем
            if updated_project.start_date_fact and updated_project.start_date_fact > date.today():
                messages.error(request, 'Фактическая дата начала не может быть в будущем.')
                return redirect('project_edit', project_id=project.id)

            if updated_project.end_date_fact and updated_project.end_date_fact > date.today():
                messages.error(request, 'Фактическая дата окончания не может быть в будущем.')
                return redirect('project_edit', project_id=project.id)

            new_status = updated_project.status
            if new_status and new_status.name == 'Завершён':
                unfinished_tasks = Task.objects.filter(
                    project=project
                ).exclude(status__name='Готово').count()
                if unfinished_tasks > 0:
                    messages.error(
                        request,
                        f'Нельзя завершить проект: {unfinished_tasks} задач(и) ещё не выполнены. '
                        f'Завершите или переназначьте их перед закрытием проекта.'
                    )
                    return redirect('project_edit', project_id=project.id)
            old_participants = set(project.participants.all())
            new_participant_ids = set(int(pid) for pid in request.POST.getlist('participants'))
            new_participants = set(User.objects.filter(id__in=new_participant_ids))
            removed_participants = old_participants - new_participants

            if removed_participants:
                for user in removed_participants:
                    active_tasks = Task.objects.filter(
                        project=project,
                        assigned_to=user
                    ).exclude(status__name='Готово')
                    if active_tasks.exists():
                        task_list = ', '.join(active_tasks.values_list('title', flat=True)[:3])
                        messages.error(
                            request,
                            f'Нельзя удалить участника {user.get_full_name() or user.username}: '
                            f'у него есть незавершённые задачи ({task_list}...). '
                            f'Переназначьте их перед удалением.'
                        )
                        return redirect('project_edit', project_id=project.id)
            form.save()
            messages.success(request, 'Проект обновлён.')
            return redirect('project_detail', project_id=project.id)
        else:
            messages.error(request, 'Проверьте правильность заполнения полей.')
    else:
        form = ProjectForm(instance=project, user=request.user)

    employee_ids = Employee.objects.filter(manager=request.user).values_list('employee_id', flat=True)
    users = User.objects.filter(id__in=employee_ids)
    priorities = Priority.objects.all()

    context = {
        'form': form,
        'project': project,
        'users': users,
        'priorities': priorities,
    }
    return render(request, 'resource_planning/project_edit.html', context)

@login_required
def team(request):
    project_id = request.GET.get('project_id', '')
    employees = Employee.objects.filter(manager=request.user).select_related('employee')

    if project_id:
        employees = employees.filter(employee__participating_projects__id=project_id)

    team_data = []
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    for emp in employees:
        user = emp.employee

        # Задачи по статусам
        tasks_in_work = Task.objects.filter(assigned_to=user, status__name='В работе').count()
        tasks_on_review = Task.objects.filter(assigned_to=user, status__name='На проверке').count()
        tasks_done = Task.objects.filter(assigned_to=user, status__name='Готово').count()
        tasks_overdue = Task.objects.filter(
            assigned_to=user,
            planned_end_date__lt=timezone.now()
        ).exclude(status__name='Готово').count()

        # Проекты сотрудника
        projects = Project.objects.filter(participants=user)

        # Загрузка на текущей неделе
        planned = TaskAssignment.objects.filter(
            user=user,
            task__planned_end_date__gte=week_start,
            task__planned_end_date__lte=week_end
        ).aggregate(total=models.Sum('planned_hours'))['total'] or 0

        available = 40
        load_percent = int((planned / available) * 100) if available > 0 else 0

        team_data.append({
            'user': user,
            'tasks_in_work': tasks_in_work,
            'tasks_on_review': tasks_on_review,
            'tasks_done': tasks_done,
            'tasks_overdue': tasks_overdue,
            'projects': projects,
            'load_percent': load_percent,
        })

    projects = Project.objects.filter(manager=request.user)
    absence_types = AbsenceType.objects.all()
    context = {
        'team_data': team_data,
        'projects': projects,
        'current_project_id': project_id,
        'absence_types': absence_types,
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
        # Проверка, существует ли пользователь с таким email
        user = User.objects.filter(email=email).first()
        if user:
            # Если пользователь уже существует, то проверяем, не добавлен ли уже
            if Employee.objects.filter(manager=request.user, employee=user).exists():
                messages.warning(request, f'{user.get_full_name() or user.username} уже в вашей команде')
            else:
                Employee.objects.create(manager=request.user, employee=user)
                messages.success(request, f'{user.get_full_name() or user.username} добавлен в команду')
        else:
            username = email.split('@')[0] # Создание нового пользователя
            if User.objects.filter(username=username).exists(): # Проверка уникальности логина
                username = f"{username}{random.randint(100, 999)}"

            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

            user = User.objects.create_user(
                username=username, email=email, password=password, first_name=first_name, last_name=last_name)
            executor_group = Group.objects.get(name='Исполнитель')
            user.groups.add(executor_group)
            Employee.objects.create(manager=request.user, employee=user)
            messages.warning(
                request,
                f'ВАЖНО! Сотрудник создан. Логин: {username}, Пароль: {password}. '
                f'Это сообщение отображается лишь один раз. Скопируйте их сейчас и передайте сотруднику.'
            )
        return redirect('team')
    return redirect('team')


def redirect_by_role(request):
    user = request.user
    if user.groups.filter(name='Руководитель проекта').exists():
        return redirect('/resource/')
    elif user.groups.filter(name='Исполнитель').exists():
        return redirect('/tasks/board')
    elif user.groups.filter(name='Директор').exists():
        return redirect('/tasks/board')  # позже — десктоп Насти

    return redirect('dashboard')

def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    done_status = TaskStatus.objects.get(name='Готово')
    work_status = TaskStatus.objects.get(name='В работе')

    pending_requests = ExecutorChangeRequest.objects.filter(task=task, is_approved=False)
    employee_ids = Employee.objects.filter(manager=request.user).values_list('employee_id', flat=True)
    users = User.objects.filter(id__in=employee_ids)

    context = {
        'task': task,
        'done_status_id': done_status.id,
        'work_status_id': work_status.id,
        'pending_requests': pending_requests,
        'users': users,
    }
    return render(request, 'resource_planning/task_detail.html', context)


def approve_executor_change(request, request_id):
    req = get_object_or_404(ExecutorChangeRequest, id=request_id)
    req.is_approved = True
    req.save()
    req.task.assigned_to = req.to_user
    req.task.save()

    Notification.objects.create(
        user=req.to_user,
        task=req.task,
        message=f'{request.user.get_full_name() or request.user.username} назначил вас исполнителем задачи «{req.task.title}».'
    )

    messages.success(request, 'Исполнитель изменён.')
    return redirect('task_detail_view', task_id=req.task.id)


@csrf_exempt
@login_required
def update_task_status(request, task_id):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        data = json.loads(request.body)
        status_id = data.get('status_id')

        if status_id:
            try:
                new_status = TaskStatus.objects.get(id=status_id)
                task.status = new_status
                task.save()

                # Если задача переведена в «Готово» — считаем фактические часы
                if new_status.name == 'Готово' and task.planned_start_date and task.planned_end_date:
                    assignment = TaskAssignment.objects.filter(task=task).first()
                    if assignment:
                        # Считаем рабочие дни между началом и концом
                        delta_days = (task.planned_end_date.date() - task.planned_start_date.date()).days + 1
                        delta_days = max(1, delta_days)  # минимум 1 день
                        auto_hours = delta_days * 8
                        assignment.actual_hours += auto_hours
                        assignment.save()

                if task.assigned_to:
                    Notification.objects.create(
                        user=task.assigned_to,
                        task=task,
                        message=f'{request.user.get_full_name() or request.user.username} '
                                f'перевёл задачу «{task.title}» в статус «{new_status.name}».'
                    )

                return JsonResponse({'success': True, 'status': new_status.name})
            except TaskStatus.DoesNotExist:
                return JsonResponse({'error': 'Статус не найден'}, status=404)

    return JsonResponse({'error': 'Неверный запрос'}, status=400)


@login_required
def notifications_list(request):
    project_id = request.GET.get('project_id', '')

    notifications = Notification.objects.filter(user=request.user).select_related('task__project').order_by(
        '-created_at')

    if project_id:
        notifications = notifications.filter(task__project_id=project_id)

    unread_count = notifications.filter(is_read=False).count()

    # Список проектов для фильтра (только те, по которым есть уведомления)
    projects_with_notifications = Project.objects.filter(
        tasks__notification__user=request.user
    ).distinct()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'projects': projects_with_notifications,
        'current_project_id': project_id,
    }
    return render(request, 'resource_planning/notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notifications_list')


def reject_executor_change(request, request_id):
    req = get_object_or_404(ExecutorChangeRequest, id=request_id)

    Notification.objects.create(
        user=req.from_user,
        task=req.task,
        message=f'{request.user.get_full_name() or request.user.username} отклонил ваш запрос на смену исполнителя в задаче «{req.task.title}».'
    )

    req.delete()
    messages.success(request, 'Запрос на смену исполнителя отклонён.')
    return redirect('task_detail_view', task_id=req.task.id)


def assign_executor(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        executor_id = request.POST.get('executor_id')
        if executor_id:
            try:
                new_executor = User.objects.get(id=int(executor_id))
            except (User.DoesNotExist, ValueError):
                messages.error(request, 'Исполнитель не найден.')
                return redirect('task_detail_view', task_id=task.id)

            old_executor = task.assigned_to
            task.assigned_to = new_executor
            task.save()

            Notification.objects.create(
                user=new_executor,
                task=task,
                message=f'{request.user.get_full_name() or request.user.username} назначил вас исполнителем задачи «{task.title}».'
            )

            if old_executor and old_executor != new_executor:
                Notification.objects.create(
                    user=old_executor,
                    task=task,
                    message=f'{request.user.get_full_name() or request.user.username} снял вас с задачи «{task.title}».'
                )

            messages.success(request, 'Исполнитель назначен.')
        else:
            messages.error(request, 'Не выбран исполнитель.')
    return redirect('task_detail_view', task_id=task.id)

@login_required
def profile(request):
    return render(request, 'resource_planning/profile.html')

@login_required
def project_delete(request, project_id):
    project = get_object_or_404(Project, id=project_id, manager=request.user)
    if request.method == 'POST':
        project.delete()
        messages.success(request, f'Проект «{project.name}» удалён.')
        return redirect('project_list')
    return render(request, 'resource_planning/project_delete.html', {'project': project})


def add_absence(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        absence_type_id = request.POST.get('absence_type')
        reason = request.POST.get('reason', '')

        overlapping = UserAbsence.objects.filter(
            user_id=user_id,
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        if overlapping.exists():
            messages.error(request, 'У сотрудника уже есть отсутствие в этом периоде.')
            return redirect('team')

        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            if start < date.today():
                messages.error(request, 'Нельзя добавить отсутствие за прошедший период.')
                return redirect('team')

        user = get_object_or_404(User, id=user_id)
        absence_type = get_object_or_404(AbsenceType, id=absence_type_id)

        UserAbsence.objects.create(
            user=user,
            start_date=start_date,
            end_date=end_date,
            absence_type=absence_type,
            reason=reason,
        )

        messages.success(request, f'Отсутствие для {user.get_full_name() or user.username} добавлено.')

    return redirect('team')

def employee_detail(request, employee_id):
    emp_rel = get_object_or_404(Employee, manager=request.user, employee_id=employee_id)
    user = emp_rel.employee
    tasks = Task.objects.filter(assigned_to=user).select_related('project', 'status')
    projects = Project.objects.filter(participants=user)
    context = {
        'employee_user': user,
        'tasks': tasks,
        'projects': projects,
    }
    return render(request, 'resource_planning/employee_detail.html', context)

@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notifications_list')

@login_required
def all_tasks_calendar(request):
    users = User.objects.filter(is_active=True, is_superuser=False)
    return render(request, 'resource_planning/calendar.html', {'users': users})

def all_tasks_api(request):
    tasks = Task.objects.filter(project__manager=request.user).select_related('status', 'assigned_to', 'project')
    events = []
    for task in tasks:
        events.append({
            'id': task.id,
            'title': f'[{task.project.name}] {task.title}',
            'start': task.planned_start_date.isoformat() if task.planned_start_date else task.created_at.isoformat(),
            'end': task.planned_end_date.isoformat() if task.planned_end_date else None,
            'color': get_status_color(task.status.name if task.status else ''),
            'url': f'/resource/task/{task.id}/',
            'extendedProps': {
                'status': task.status.name if task.status else 'Без статуса',
                'assignee': task.assigned_to.get_full_name() if task.assigned_to else 'Не назначен',
                'project': task.project.name,
            }
        })
    return JsonResponse(events, safe=False)

@login_required
def remove_employee(request, employee_id):
    # Проверяем, есть ли у сотрудника незавершённые задачи в проектах руководителя
    active_tasks = Task.objects.filter(
        assigned_to_id=employee_id,
        project__manager=request.user
    ).exclude(status__name='Готово')

    if active_tasks.exists():
        task_list = ', '.join(active_tasks.values_list('title', flat=True)[:3])
        messages.error(
            request,
            f'Нельзя удалить сотрудника: у него есть незавершённые задачи '
            f'({active_tasks.count()} шт., включая: {task_list}...). '
            f'Переназначьте эти задачи перед удалением.'
        )
        return redirect('team')

    Employee.objects.filter(manager=request.user, employee_id=employee_id).delete()
    messages.success(request, 'Сотрудник удалён из команды.')
    return redirect('team')