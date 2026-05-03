from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from task_management.models import Task, Notification


class Command(BaseCommand):
    help = 'Проверяет дедлайны и создаёт оповещения'

    def handle(self, *args, **kwargs):
        tomorrow = timezone.now() + timedelta(days=1)
        today = timezone.now()

        # Задачи с дедлайном завтра
        tasks_due_tomorrow = Task.objects.filter(
            planned_end_date__date=tomorrow.date(),
            parent_task__isnull=True
        ).exclude(status__name__in=['Готово', 'Заблокирована'])

        for task in tasks_due_tomorrow:
            if task.assigned_to:
                Notification.objects.get_or_create(
                    user=task.assigned_to,
                    task=task,
                    message=f'Дедлайн задачи "{task.title}" завтра ({task.planned_end_date.strftime("%d.%m.%Y")})!',
                    defaults={'created_at': timezone.now()}
                )

        # Просроченные задачи
        overdue_tasks = Task.objects.filter(
            planned_end_date__lt=today,
            parent_task__isnull=True
        ).exclude(status__name__in=['Готово', 'Заблокирована'])

        for task in overdue_tasks:
            if task.assigned_to:
                Notification.objects.get_or_create(
                    user=task.assigned_to,
                    task=task,
                    message=f'Задача "{task.title}" просрочена! Дедлайн был {task.planned_end_date.strftime("%d.%m.%Y")}.',
                    defaults={'created_at': timezone.now()}
                )

        self.stdout.write(
            self.style.SUCCESS(f'Проверено: {tasks_due_tomorrow.count()} завтра, {overdue_tasks.count()} просрочено'))