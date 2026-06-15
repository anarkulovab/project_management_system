from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
import json

from .models import Task, TaskStatus, Comment, TaskHistory, Notification, ExecutorChangeRequest
from resource_planning.models import Project


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def is_task_locked(task):
    """Задача заморожена для исполнителя"""
    return task.status.name.strip().lower() in ['на проверке', 'готово']


def is_parent_locked(task):
    """Родительская задача заморожена"""
    return task.parent_task and task.parent_task.status.name.strip().lower() in ['на проверке', 'готово']


# ============================================================
# 1. КАНБАН-ДОСКА
# ============================================================

@login_required
def kanban_board(request):
    statuses = TaskStatus.objects.all().order_by('order')

    tasks = Task.objects.filter(
        assigned_to=request.user,
        parent_task__isnull=True
    ).select_related('project', 'status').prefetch_related('subtasks')

    project_id = request.GET.get('project')
    priority = request.GET.get('priority')

    if project_id:
        tasks = tasks.filter(project_id=project_id)
    if priority:
        tasks = tasks.filter(priority=priority)

    today = timezone.now().date()

    # Автоперенос из «Запланирована» в «Новая»
    planned_status = TaskStatus.objects.filter(name='Запланирована').first()
    new_status = TaskStatus.objects.filter(name='Новая').first()
    if planned_status and new_status:
        due_tasks = tasks.filter(status=planned_status, planned_start_date__date=today)
        for t in due_tasks:
            old_status = t.status.name
            t.status = new_status
            t.save()
            TaskHistory.objects.create(
                task=t, user=t.assigned_to,
                changed_field='status', old_value=old_status, new_value=new_status.name,
            )
            Notification.objects.create(
                user=t.assigned_to, task=t,
                message=f'Задача «{t.title}» перенесена в «Новая». Дата начала выполнения — сегодня.'
            )

    tasks = Task.objects.filter(
        assigned_to=request.user, parent_task__isnull=True
    ).select_related('project', 'status').prefetch_related('subtasks')

    if project_id:
        tasks = tasks.filter(project_id=project_id)
    if priority:
        tasks = tasks.filter(priority=priority)

    for status in statuses:
        status.filtered_tasks = tasks.filter(status=status)
        status.task_count = status.filtered_tasks.count()

    projects = Project.objects.all()

    return render(request, 'task_management/kanban_board.html', {
        'statuses': statuses,
        'projects': projects,
        'selected_project': project_id,
        'selected_priority': priority,
    })


# ============================================================
# 2. ОБНОВЛЕНИЕ СТАТУСА ЗАДАЧИ (DRAG-AND-DROP + ГАЛОЧКИ ПОДЗАДАЧ)
# ============================================================

@csrf_exempt
@login_required
def update_task_status(request, task_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Неверный метод'})

    task = get_object_or_404(Task, id=task_id)

    # Права
    if request.user != task.assigned_to and request.user != task.author:
        return JsonResponse({'success': False, 'error': 'Нет прав на изменение статуса'})

    data = json.loads(request.body)
    new_status_id = data.get('status_id')
    new_status = get_object_or_404(TaskStatus, id=new_status_id)

    old_status_name = task.status.name.strip().lower()
    new_status_name = new_status.name.strip().lower()

    is_manager = request.user.groups.filter(name='Руководитель проекта').exists()
    is_subtask = task.parent_task is not None

    # === ПОДЗАДАЧИ ===
    if is_subtask:
        # Блокировка подзадач, если родитель на проверке или готово
        if is_parent_locked(task):
            return JsonResponse({
                'success': False,
                'error': 'Нельзя изменять подзадачи у задачи на проверке или в статусе "Готово".'
            })

        task.status = new_status
        task.save()

        TaskHistory.objects.create(
            task=task, user=request.user,
            changed_field='status', old_value=old_status_name, new_value=new_status_name,
        )
        return JsonResponse({'success': True})

    # === ОСНОВНЫЕ ЗАДАЧИ ===

    # Блокировка для исполнителя
    if is_task_locked(task) and not is_manager:
        return JsonResponse({
            'success': False,
            'error': 'Задача заморожена. Только руководитель может изменить её статус.'
        })

    # Проверка подзадач перед отправкой на проверку
    if new_status_name == 'на проверке':
        if task.subtasks.exclude(status__name='Готово').exists():
            return JsonResponse({
                'success': False,
                'error': 'Сначала завершите все подзадачи.'
            })

    # Только руководитель
    manager_only = [
        ('на проверке', 'готово'),
        ('на проверке', 'в работе'),
        ('готово', 'в работе'),
    ]
    if (old_status_name, new_status_name) in manager_only and not is_manager:
        return JsonResponse({
            'success': False,
            'error': 'Только руководитель может выполнить это действие.'
        })

    # Запрет ручного переноса в «Запланирована»
    if new_status_name == 'запланирована':
        return JsonResponse({
            'success': False,
            'error': 'Нельзя вручную перенести задачу в «Запланирована».'
        })

    # Полностью запрещённые переходы
    forbidden = [
        ('новая', 'на проверке'),
        ('новая', 'готово'),
        ('в работе', 'готово'),
        ('в работе', 'новая'),
        ('на проверке', 'новая'),
        ('готово', 'на проверке'),
        ('готово', 'новая'),
        ('готово', 'запланирована'),
    ]
    if (old_status_name, new_status_name) in forbidden:
        return JsonResponse({
            'success': False,
            'error': 'Этот переход запрещён.'
        })

    # Сохранение
    task.status = new_status
    task.save()

    TaskHistory.objects.create(
        task=task, user=request.user,
        changed_field='status', old_value=old_status_name, new_value=new_status_name,
    )

    # Оповещения
    if new_status_name == 'на проверке' and task.project.manager:
        Notification.objects.create(
            user=task.project.manager, task=task,
            message=f'{request.user.get_full_name() or request.user.username} перевёл задачу "{task.title}" в статус "На проверке".'
        )
    elif new_status_name == 'готово' and old_status_name == 'на проверке' and task.assigned_to:
        Notification.objects.create(
            user=task.assigned_to, task=task,
            message=f'Руководитель принял задачу "{task.title}".'
        )
    elif new_status_name == 'в работе' and old_status_name == 'на проверке' and task.assigned_to:
        Notification.objects.create(
            user=task.assigned_to, task=task,
            message=f'Руководитель отклонил задачу "{task.title}". Требуется доработка.'
        )
    elif new_status_name == 'в работе' and old_status_name == 'готово' and task.assigned_to:
        Notification.objects.create(
            user=task.assigned_to, task=task,
            message=f'Руководитель переоткрыл задачу "{task.title}".'
        )

    return JsonResponse({'success': True})


# ============================================================
# 3. ДЕТАЛИ ЗАДАЧИ
# ============================================================

@login_required
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if task.parent_task:
        return render(request, 'task_management/access_denied.html', {
            'task': task,
            'message': 'Подзадачи не имеют отдельной страницы.'
        }, status=403)

    is_manager = request.user.groups.filter(name='Руководитель проекта').exists()
    is_admin = request.user.is_staff

    if not is_manager and not is_admin:
        if request.user != task.assigned_to and request.user != task.author:
            return render(request, 'task_management/access_denied.html', {
                'task': task,
                'message': 'У вас нет доступа к этой задаче.'
            }, status=403)

    comments = task.comments.all().order_by('created_at')
    history = task.history.all().order_by('-changed_at')

    return render(request, 'task_management/task_detail.html', {
        'task': task,
        'comments': comments,
        'history': history,
    })


# ============================================================
# 4. КОММЕНТАРИИ
# ============================================================

@login_required
def add_comment(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if task.status.name == 'Готово':
        messages.error(request, 'Нельзя комментировать завершённую задачу.')
        #return redirect('task-detail', task_id=task.id)
        return redirect(request.META.get('HTTP_REFERER', 'task-detail'))

    if request.method == 'POST':
        text = request.POST.get('text')
        if text:
            Comment.objects.create(task=task, author=request.user, text=text)

            if task.project.manager and request.user != task.project.manager:
                Notification.objects.create(
                    user=task.project.manager, task=task,
                    message=f'{request.user.get_full_name() or request.user.username} оставил(а) комментарий к задаче "{task.title}".'
                )
            if task.assigned_to and request.user == task.project.manager:
                Notification.objects.create(
                    user=task.assigned_to, task=task,
                    message=f'Руководитель {request.user.get_full_name() or request.user.username} оставил(а) комментарий к задаче "{task.title}".'
                )

    # Возвращаем туда, откуда пришли
    referer = request.META.get('HTTP_REFERER', '')
    if referer:
        return redirect(referer)
    return redirect('task-detail', task_id=task.id)


# ============================================================
# 5. СОЗДАНИЕ ЗАДАЧИ (руководитель)
# ============================================================

@login_required
def create_task(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Только руководитель может создавать задачи")
    if request.method == 'POST':
        title = request.POST.get('title')
        project_id = request.POST.get('project')
        if title and project_id:
            project = get_object_or_404(Project, id=project_id)
            assigned_to_id = request.POST.get('assigned_to')
            assigned_to = get_object_or_404(User, id=assigned_to_id) if assigned_to_id else None
            default_status = TaskStatus.objects.get(name='Новая')
            Task.objects.create(
                title=title,
                description=request.POST.get('description', ''),
                priority=request.POST.get('priority', 'medium'),
                planned_end_date=request.POST.get('planned_end_date'),
                project=project, assigned_to=assigned_to,
                author=request.user, status=default_status,
            )
            messages.success(request, f'Задача "{title}" успешно создана!')
            return redirect('kanban-board')

    projects = Project.objects.all()
    users = User.objects.all()
    return render(request, 'task_management/create_task.html', {
        'projects': projects, 'users': users,
    })


# ============================================================
# 6. ЗАПРОС СМЕНЫ ИСПОЛНИТЕЛЯ
# ============================================================

@login_required
def request_executor_change(request, task_id):
    task = get_object_or_404(Task, id=task_id, assigned_to=request.user)

    if task.status.name in ['На проверке', 'Готово']:
        return render(request, 'task_management/access_denied.html', {
            'task': task,
            'message': 'Нельзя менять исполнителя для задачи в статусе "На проверке" или "Готово".'
        }, status=403)

    if request.method == 'POST':
        to_user = get_object_or_404(User, id=request.POST.get('to_user'))
        reason = request.POST.get('reason', '')

        ExecutorChangeRequest.objects.create(
            task=task, from_user=request.user, to_user=to_user, reason=reason,
        )
        Notification.objects.create(
            user=request.user, task=task,
            message=f'Вы запросили передачу задачи "{task.title}" сотруднику {to_user.get_full_name() or to_user.username}.'
        )
        TaskHistory.objects.create(
            task=task, user=request.user,
            changed_field='Запрос смены исполнителя',
            old_value=request.user.get_full_name() or request.user.username,
            new_value=f'{to_user.get_full_name() or to_user.username}',
        )
        if task.project.manager:
            Notification.objects.create(
                user=task.project.manager, task=task,
                message=f'{request.user.get_full_name() or request.user.username} просит передать задачу "{task.title}" сотруднику {to_user.get_full_name() or to_user.username}. Причина: {reason or "не указана"}.'
            )
        messages.success(request, 'Запрос отправлен руководителю.')
        return redirect('task-detail', task_id=task.id)

    participants = task.project.participants.exclude(id=request.user.id)
    return render(request, 'task_management/request_change.html', {
        'task': task, 'participants': participants,
    })


# ============================================================
# 7. ЛИЧНЫЙ КАБИНЕТ
# ============================================================

@login_required
def personal_dashboard(request):
    user = request.user
    statuses = TaskStatus.objects.all().order_by('order')
    user_tasks = Task.objects.filter(
        assigned_to=user, parent_task__isnull=True
    ).select_related('project', 'status')

    for status in statuses:
        status.task_count = user_tasks.filter(status=status).count()

    total_tasks = user_tasks.count()
    overdue_tasks = user_tasks.filter(
        planned_end_date__lt=timezone.now()
    ).exclude(status__name__in=['Готово'])

    try:
        done_status = TaskStatus.objects.get(name='Готово')
        completed_tasks = user_tasks.filter(status=done_status).count()
    except TaskStatus.DoesNotExist:
        completed_tasks = 0

    return render(request, 'task_management/personal_dashboard.html', {
        'user_tasks': user_tasks, 'statuses': statuses,
        'total_tasks': total_tasks, 'overdue_tasks': overdue_tasks,
        'completed_tasks': completed_tasks,
    })


# ============================================================
# 8-10. ПРОЕКТЫ, ПОДЗАДАЧИ, УВЕДОМЛЕНИЯ, СМЕНА ПАРОЛЯ...
# ============================================================

@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    is_manager = request.user.groups.filter(name='Руководитель проекта').exists()
    is_participant = project.participants.filter(id=request.user.id).exists()
    if not is_manager and not is_participant:
        return render(request, 'task_management/access_denied.html', {
            'task': project, 'message': 'У вас нет доступа к этому проекту.'
        }, status=403)
    user_tasks = Task.objects.filter(project=project, assigned_to=request.user, parent_task__isnull=True)
    return render(request, 'task_management/project_detail.html', {
        'project': project,
        'total_user_tasks': user_tasks.count(),
        'done_user_tasks': user_tasks.filter(status__name='Готово').count(),
    })


@login_required
def project_list(request):
    user = request.user
    is_manager = user.groups.filter(name='Руководитель проекта').exists()
    if is_manager:
        projects = Project.objects.filter(manager=user).order_by('-created_at')
    else:
        projects = Project.objects.filter(participants=user).order_by('-created_at')
    for p in projects:
        p.task_count = Task.objects.filter(project=p, assigned_to=user, parent_task__isnull=True).count()
        p.done_count = Task.objects.filter(project=p, assigned_to=user, status__name='Готово', parent_task__isnull=True).count()
    return render(request, 'task_management/project_list.html', {'projects': projects, 'is_manager': is_manager})


@login_required
def create_subtask(request, parent_task_id):
    parent_task = get_object_or_404(Task, id=parent_task_id)
    if parent_task.status.name.strip().lower() in ['на проверке', 'готово']:
        return render(request, 'task_management/access_denied.html', {
            'task': parent_task, 'message': 'Нельзя создавать подзадачи у задачи на проверке или завершённой.'
        }, status=403)
    if request.user != parent_task.assigned_to and request.user != parent_task.author:
        return render(request, 'task_management/access_denied.html', {
            'task': parent_task, 'message': 'Нет прав.'
        }, status=403)
    if request.method == 'POST' and request.POST.get('title'):
        Task.objects.create(
            title=request.POST.get('title'), description=request.POST.get('description', ''),
            priority='low', planned_end_date=parent_task.planned_end_date,
            project=parent_task.project, assigned_to=request.user, author=request.user,
            status=TaskStatus.objects.get(name='Новая'), parent_task=parent_task,
        )
        messages.success(request, 'Подзадача создана!')
        return redirect('task-detail', task_id=parent_task.id)
    return render(request, 'task_management/create_subtask.html', {'parent_task': parent_task})


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    return render(request, 'task_management/notifications.html', {'notifications': notifications, 'unread_count': unread_count})


@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notifications')


@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notifications')


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Пароль успешно изменён.')
            return redirect('personal-dashboard')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'task_management/change_password.html', {'form': form})


@login_required
def change_username(request):
    if request.method == 'POST':
        new_username = request.POST.get('username')
        if new_username and new_username != request.user.username:
            if User.objects.filter(username=new_username).exists():
                messages.error(request, 'Этот логин уже занят.')
            else:
                request.user.username = new_username
                request.user.save()
                messages.success(request, 'Логин успешно изменён.')
                return redirect('personal-dashboard')
    return redirect('personal-dashboard')


@login_required
def approve_executor_change(request, request_id):
    req = get_object_or_404(ExecutorChangeRequest, id=request_id)
    if request.user != req.task.project.manager:
        return HttpResponseForbidden("Только руководитель может одобрить")
    old_executor = req.task.assigned_to
    req.is_approved = True
    req.save()
    req.task.assigned_to = req.to_user
    req.task.save()
    manager_name = req.task.project.manager.get_full_name() or req.task.project.manager.username
    Notification.objects.create(user=req.to_user, task=req.task, message=f'{manager_name} передал(а) вам задачу "{req.task.title}".')
    Notification.objects.create(user=old_executor, task=req.task, message=f'Руководитель одобрил передачу задачи "{req.task.title}" сотруднику {req.to_user.get_full_name() or req.to_user.username}.')
    messages.success(request, 'Исполнитель изменён.')
    return redirect('task-detail', task_id=req.task.id)


@login_required
def delete_subtask(request, subtask_id):
    subtask = get_object_or_404(Task, id=subtask_id)
    if not subtask.parent_task:
        return redirect('kanban-board')
    parent_task = subtask.parent_task
    if request.user != parent_task.assigned_to and request.user != parent_task.author:
        return render(request, 'task_management/access_denied.html', {'task': subtask, 'message': 'Нет прав.'}, status=403)
    if parent_task.status.name in ['На проверке', 'Готово']:
        messages.error(request, 'Нельзя удалять подзадачи у задачи на проверке или завершённой.')
        return redirect('task-detail', task_id=parent_task.id)
    subtask.delete()
    messages.success(request, 'Подзадача удалена.')
    return redirect('task-detail', task_id=parent_task.id)