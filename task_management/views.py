from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from .models import Task, TaskStatus
import json
from .models import Task, TaskStatus, Comment, TaskHistory, Notification
from .models import Task, TaskStatus, Comment, TaskHistory, Notification, ExecutorChangeRequest
from django.contrib import messages



@login_required
def kanban_board(request):
    from resource_planning.models import Project

    statuses = TaskStatus.objects.all().order_by('order')

    # Получаем задачи текущего пользователя (только основные, не подзадачи)
    tasks = Task.objects.filter(
        assigned_to=request.user,
        parent_task__isnull=True
    ).select_related('project', 'status').prefetch_related('subtasks')

    # ФИЛЬТРЫ
    project_id = request.GET.get('project')
    priority = request.GET.get('priority')

    if project_id:
        tasks = tasks.filter(project_id=project_id)
    if priority:
        tasks = tasks.filter(priority=priority)

    today = timezone.now().date()

    # Автоперенос запланированных задач с сегодняшней датой начала в «Новая»
    planned_status = TaskStatus.objects.filter(name='Запланирована').first()
    new_status = TaskStatus.objects.filter(name='Новая').first()
    if planned_status and new_status:
        due_tasks = tasks.filter(status=planned_status, planned_start_date__date=today)
        for t in due_tasks:
            old_status = t.status.name
            t.status = new_status
            t.save()
            TaskHistory.objects.create(
                task=t,
                user=t.assigned_to,
                changed_field='status',
                old_value=old_status,
                new_value=new_status.name,
            )
            Notification.objects.create(
                user=t.assigned_to,
                task=t,
                message=f'Задача «{t.title}» перенесена в «Новая». Дата начала выполнения — сегодня.'
            )

    # Обновляем tasks после возможного переноса
    tasks = Task.objects.filter(
        assigned_to=request.user,
        parent_task__isnull=True
    ).select_related('project', 'status').prefetch_related('subtasks')

    if project_id:
        tasks = tasks.filter(project_id=project_id)
    if priority:
        tasks = tasks.filter(priority=priority)

    # Добавляем отфильтрованные задачи к каждому статусу
    for status in statuses:
        status.filtered_tasks = tasks.filter(status=status)
        status.task_count = status.filtered_tasks.count()
        # Для каждой задачи в колонке «Запланирована» проверяем, наступила ли дата
        if status.name == 'Запланирована':
            for task in status.filtered_tasks:
                task.is_active = task.planned_start_date and task.planned_start_date.date() <= today
                task.start_date_display = task.planned_start_date.strftime('%d.%m.%Y') if task.planned_start_date else '—'
        else:
            for task in status.filtered_tasks:
                task.is_active = True

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

        is_manager = request.user.groups.filter(name='Руководитель проекта').exists()
        is_subtask = task.parent_task is not None

        # Для подзадач разрешаем любые переходы
        if is_subtask:
            task.status = new_status
            task.save()

            from .models import TaskHistory
            TaskHistory.objects.create(
                task=task,
                user=request.user,
                changed_field='status',
                old_value=old_status_name,
                new_value=new_status_name,
            )
            return JsonResponse({'success': True})

        # Нельзя отправить на проверку, если есть незавершённые подзадачи
        if new_status_name == 'на проверке' and not is_subtask:
            unfinished_subtasks = task.subtasks.exclude(status__name='Готово').exists()
            if unfinished_subtasks:
                return JsonResponse({
                    'success': False,
                    'error': 'Нельзя отправить задачу на проверку, пока не выполнены все подзадачи.'
                })

        # Переходы, доступные только руководителю
        manager_only_transitions = [
            ('на проверке', 'готово'),
            ('на проверке', 'в работе'),
            ('готово', 'в работе'),
        ]

        if (old_status_name, new_status_name) in manager_only_transitions:
            if not is_manager:
                return JsonResponse({
                    'success': False,
                    'error': 'Только руководитель может выполнить это действие.'
                })
        # Нельзя вручную перенести в «Запланирована»
        if new_status_name == 'запланирована':
            return JsonResponse({
                'success': False,
                'error': 'Нельзя вручную перенести задачу в «Запланирована». Этот статус назначается автоматически при создании задачи с будущей датой начала.'
            })
        # Полностью запрещённые переходы
        forbidden_transitions = [
            ('новая', 'на проверке'),
            ('новая', 'готово'),
            ('в работе', 'готово'),
            ('в работе', 'новая'),
            ('на проверке', 'новая'),
        ]

        if (old_status_name, new_status_name) in forbidden_transitions:
            messages_dict = {
                ('новая', 'на проверке'): 'Нельзя отправить на проверку, не начав работу.',
                ('новая', 'готово'): 'Задача должна быть выполнена перед завершением.',
                ('в работе', 'готово'): 'Задача должна пройти проверку руководителем.',
                ('в работе', 'новая'): 'Нельзя вернуть задачу в статус "Новая".',
                ('на проверке', 'новая'): 'Нельзя сбросить задачу до "Новой".',
            }
            return JsonResponse({
                'success': False,
                'error': messages_dict.get((old_status_name, new_status_name), 'Этот переход запрещён.')
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

        # Оповещения
        from .models import Notification

        if new_status_name == 'на проверке' and not is_subtask:
            if task.project.manager:
                Notification.objects.create(
                    user=task.project.manager,
                    task=task,
                    message=f'Исполнитель {request.user} перевёл задачу "{task.title}" в статус "На проверке".'
                )

        elif new_status_name == 'готово' and old_status_name == 'на проверке':
            if task.assigned_to:
                Notification.objects.create(
                    user=task.assigned_to,
                    task=task,
                    message=f'Руководитель принял задачу "{task.title}". Статус: Готово ✅'
                )

        elif new_status_name == 'в работе' and old_status_name == 'на проверке':
            if task.assigned_to:
                Notification.objects.create(
                    user=task.assigned_to,
                    task=task,
                    message=f'Руководитель отклонил задачу "{task.title}". Требуется доработка.'
                )

        elif new_status_name == 'в работе' and old_status_name == 'готово':
            if task.assigned_to:
                Notification.objects.create(
                    user=task.assigned_to,
                    task=task,
                    message=f'Руководитель переоткрыл задачу "{task.title}".'
                )

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Неверный метод'})
@login_required
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    # Проверка доступа: только исполнитель или автор
    is_manager = request.user.groups.filter(name='Руководитель проекта').exists()
    is_admin = request.user.is_staff

    if not is_manager and not is_admin:
        if request.user != task.assigned_to and request.user != task.author:
            return render(request, 'task_management/access_denied.html', {
                'task': task,
                'message': 'У вас нет доступа к этой задаче.'
            }, status=403)

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


@login_required
def request_executor_change(request, task_id):
    task = get_object_or_404(Task, id=task_id, assigned_to=request.user)

    if request.method == 'POST':
        to_user_id = request.POST.get('to_user')
        reason = request.POST.get('reason', '')

        to_user = get_object_or_404(User, id=to_user_id)

        req = ExecutorChangeRequest.objects.create(
            task=task,
            from_user=request.user,
            to_user=to_user,
            reason=reason,
        )
        # Оповещение себе
        # Оповещение себе
        Notification.objects.create(
            user=request.user,
            task=task,
            message=f'Вы запросили передачу задачи "{task.title}" сотруднику {to_user}. Ожидайте решения руководителя.'
        )

        # Запись в историю
        TaskHistory.objects.create(
            task=task,
            user=request.user,
            changed_field='executor_change_request',
            old_value=str(request.user),
            new_value=f'Запрос на {to_user}',
        )

        # Оповещение руководителю
        if task.project.manager:
            Notification.objects.create(
                user=task.project.manager,
                task=task,
                message=f'{request.user} просит передать задачу "{task.title}" сотруднику {to_user}.'
            )

        messages.success(request, '✅ Запрос на смену исполнителя отправлен руководителю.')
        return redirect('task-detail', task_id=task.id)

    # GET — показать форму
    project_participants = task.project.participants.exclude(id=request.user.id)

    context = {
        'task': task,
        'participants': project_participants,
    }
    return render(request, 'task_management/request_change.html', context)

from django.utils import timezone


@login_required
def personal_dashboard(request):
    user = request.user
    statuses = TaskStatus.objects.all().order_by('order')

    # Только основные задачи (без подзадач)
    user_tasks = Task.objects.filter(
        assigned_to=user,
        parent_task__isnull=True
    ).select_related('project', 'status')

    # Статистика по статусам
    for status in statuses:
        status.task_count = user_tasks.filter(status=status).count()

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

@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Проверка доступа
    is_manager = request.user.groups.filter(name='Руководитель проекта').exists()
    is_participant = project.participants.filter(id=request.user.id).exists()
    is_admin = request.user.is_staff

    if not is_manager and not is_admin and not is_participant:
        return render(request, 'task_management/access_denied.html', {
            'task': project,
            'message': 'У вас нет доступа к этому проекту. Вы не являетесь участником.'
        }, status=403)

    statuses = TaskStatus.objects.all().order_by('order')

    # Все задачи проекта
    project_tasks = Task.objects.filter(project=project, parent_task__isnull=True).select_related('assigned_to', 'status')

    # Группируем по статусам
    for status in statuses:
        status.filtered_tasks = project_tasks.filter(status=status)
        status.task_count = status.filtered_tasks.filter(parent_task__isnull=True).count()

    context = {
        'project': project,
        'statuses': statuses,
        'total_tasks': project_tasks.count(),
    }
    return render(request, 'task_management/project_detail.html', context)


@login_required
def project_list(request):
    user = request.user
    # Ищем в группах, а не через is_staff
    is_manager = user.groups.filter(name='Руководитель проекта').exists()

    if is_manager:
        projects = Project.objects.filter(manager=user).order_by('-created_at')
    else:
        projects = Project.objects.filter(participants=user).order_by('-created_at')

    for project in projects:
        project.task_count = Task.objects.filter(project=project, parent_task__isnull=True).count()
        project.done_count = Task.objects.filter(project=project, status__name='Готово').count()

    context = {
        'projects': projects,
        'is_manager': is_manager,
    }
    return render(request, 'task_management/project_list.html', context)


@login_required
def create_subtask(request, parent_task_id):
    parent_task = get_object_or_404(Task, id=parent_task_id)

    # Только исполнитель или автор может создать подзадачу
    if request.user != parent_task.assigned_to and request.user != parent_task.author:
        return render(request, 'task_management/access_denied.html', {
            'task': parent_task,
            'message': 'Вы не можете создавать подзадачи к этой задаче.'
        }, status=403)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')

        if title:
            Task.objects.create(
                title=title,
                description=description or '',
                priority='low',
                planned_end_date=parent_task.planned_end_date,
                project=parent_task.project,
                assigned_to=request.user,
                author=request.user,
                status=TaskStatus.objects.get(name='Новая'),
                parent_task=parent_task,
            )
            from django.contrib import messages
            messages.success(request, f'✅ Подзадача "{title}" создана!')
            return redirect('task-detail', task_id=parent_task.id)

    context = {
        'parent_task': parent_task,
    }
    return render(request, 'task_management/create_subtask.html', context)


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    return render(request, 'task_management/notifications.html', {'notifications': notifications})


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'task_management/notifications.html', context)


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


from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
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


from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def redirect_by_role(request):
    user = request.user
    is_manager = user.groups.filter(name='Руководитель проекта').exists()

    if is_manager or user.is_staff:
        return redirect('/resource/')  # ← правильный префикс Бегимай
    else:
        return redirect('kanban-board')