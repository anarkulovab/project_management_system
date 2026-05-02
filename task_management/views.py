from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
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



        # Проверка
        if old_status_name == 'в работе' and new_status_name == 'готово':
            return JsonResponse({
                'success': False,
                'error': 'Задача должна пройти проверку руководителем!'
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