from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Task, TaskStatus
import json


@login_required
def kanban_board(request):
    statuses = TaskStatus.objects.all().order_by('order')

    # Добавляем отфильтрованные задачи к каждому статусу
    for status in statuses:
        status.filtered_tasks = status.task_set.filter(assigned_to=request.user)
        status.task_count = status.filtered_tasks.count()

    context = {
        'statuses': statuses,
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

        old_status = task.status
        new_status = get_object_or_404(TaskStatus, id=new_status_id)

        if old_status.name == 'В работе' and new_status.name == 'Готово':
            return JsonResponse({
                'success': False,
                'error': 'Задача должна пройти проверку руководителем. Сначала переведите в "На проверке".'
            })

        task.status = new_status
        task.save()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})