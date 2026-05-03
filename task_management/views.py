from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from .models import Task, TaskStatus
import json


@login_required
def kanban_board(request):
    from resource_planning.models import Project

    statuses = TaskStatus.objects.all().order_by('order')

    # Получаем задачи текущего пользователя
    tasks = Task.objects.filter(assigned_to=request.user).select_related('project', 'status')

    # ФИЛЬТРЫ
    project_id = request.GET.get('project')
    priority = request.GET.get('priority')

    if project_id:
        tasks = tasks.filter(project_id=project_id)
    if priority:
        tasks = tasks.filter(priority=priority)

    # Добавляем отфильтрованные задачи к каждому статусу
    for status in statuses:
        status.filtered_tasks = tasks.filter(status=status)
        status.task_count = status.filtered_tasks.count()

    # Все доступные проекты для фильтра
    projects = Project.objects.all()

    context = {
        'statuses': statuses,
        'projects': projects,
        'selected_project': project_id,
        'selected_priority': priority,
    }
    return render(request, 'task_management/kanban_board.html', context)
@csrf_exempt
@login_required
def update_task_status(request, task_id):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)

        if request.user != task.assigned_to and request.user != task.author:
            return JsonResponse({'success': False, 'error': 'Нет прав на изменение статуса'})

        data = json.loads(request.body)
        new_status_id = data.get('status_id')

        old_status_name = str(task.status.name).strip().lower()
        new_status = get_object_or_404(TaskStatus, id=new_status_id)
        new_status_name = str(new_status.name).strip().lower()

        # Правила переходов
        forbidden_transitions = [
            ('новая', 'на проверке'),
            ('новая', 'готово'),
            ('в работе', 'готово'),
            ('в работе', 'новая'),
            ('на проверке', 'новая'),
        ]

        if (old_status_name, new_status_name) in forbidden_transitions:
            messages = {
                ('новая', 'на проверке'): 'Нельзя отправить на проверку, не начав работу.',
                ('новая', 'готово'): 'Задача должна быть выполнена перед завершением.',
                ('в работе', 'готово'): 'Задача должна пройти проверку руководителем. Сначала переведите в "На проверке".',
                ('в работе', 'новая'): 'Нельзя вернуть задачу в статус "Новая".',
                ('на проверке', 'новая'): 'Нельзя сбросить задачу до "Новой", верните в работу.',
            }
            return JsonResponse({
                'success': False,
                'error': messages.get((old_status_name, new_status_name), 'Этот переход запрещён.')
            })

        # Запись в историю
        from .models import TaskHistory
        TaskHistory.objects.create(
            task=task,
            user=request.user,
            changed_field='status',
            old_value=old_status_name,
            new_value=new_status_name,
        )

        task.status = new_status
        task.save()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Неверный метод'})
@login_required
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    # Проверка доступа: только исполнитель или автор
    if request.user != task.assigned_to and request.user != task.author:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("У вас нет доступа к этой задаче")

    # Комментарии
    comments = task.comments.all().order_by('created_at')

    # История изменений
    history = task.history.all().order_by('-changed_at')

    context = {
        'task': task,
        'comments': comments,
        'history': history,
    }
    return render(request, 'task_management/task_detail.html', context)


from django.shortcuts import redirect


@login_required
def add_comment(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if request.method == 'POST':
        text = request.POST.get('text')
        if text:
            from .models import Comment
            Comment.objects.create(
                task=task,
                author=request.user,
                text=text
            )

    return redirect('task-detail', task_id=task.id)


from django.shortcuts import render, get_object_or_404, redirect
from resource_planning.models import Project


@login_required
def create_task(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Только руководитель может создавать задачи")
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority')
        project_id = request.POST.get('project')
        assigned_to_id = request.POST.get('assigned_to')
        planned_end_date = request.POST.get('planned_end_date')

        if title and project_id:
            project = get_object_or_404(Project, id=project_id)
            assigned_to = get_object_or_404(User, id=assigned_to_id) if assigned_to_id else None

            # Статус по умолчанию — "Новая"
            default_status = TaskStatus.objects.get(name='Новая')

            Task.objects.create(
                title=title,
                description=description,
                priority=priority or 'medium',
                planned_end_date=planned_end_date,
                project=project,
                assigned_to=assigned_to,
                author=request.user,
                status=default_status,
            )
            from django.contrib import messages

            # после создания задачи:
            messages.success(request, f'✅ Задача "{title}" успешно создана!')
            return redirect('kanban-board')

    # GET-запрос — показать форму
    projects = Project.objects.all()
    users = User.objects.all()
    statuses = TaskStatus.objects.all().order_by('order')

    context = {
        'projects': projects,
        'users': users,
        'statuses': statuses,
    }
    return render(request, 'task_management/create_task.html', context)


from django.utils import timezone


@login_required
def personal_dashboard(request):
    user = request.user
    statuses = TaskStatus.objects.all().order_by('order')

    # Все задачи пользователя
    user_tasks = Task.objects.filter(assigned_to=user).select_related('project', 'status')

    # Статистика по статусам
    for status in statuses:
        status.task_count = user_tasks.filter(status=status).count()

    # Общее количество
    total_tasks = user_tasks.count()

    # Просроченные
    overdue_tasks = user_tasks.filter(
        planned_end_date__lt=timezone.now()
    ).exclude(status__name__in=['Готово', 'Заблокирована'])

    # Выполненные
    try:
        done_status = TaskStatus.objects.get(name='Готово')
        completed_tasks = user_tasks.filter(status=done_status).count()
    except TaskStatus.DoesNotExist:
        completed_tasks = 0

    context = {
        'user_tasks': user_tasks,
        'statuses': statuses,
        'total_tasks': total_tasks,
        'overdue_tasks': overdue_tasks,
        'completed_tasks': completed_tasks,
    }
    return render(request, 'task_management/personal_dashboard.html', context)