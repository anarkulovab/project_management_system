from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from task_management.models import TaskStatus, Task
from resource_planning.models import Project, ProjectStatus, Priority
from django.utils import timezone


class Command(BaseCommand):
    help = 'Заполнение БД тестовыми данными'

    def handle(self, *args, **kwargs):
        # 1. Статусы задач
        statuses = [
            {'name': 'В работе', 'order': 1},
            {'name': 'На проверке', 'order': 2},
            {'name': 'Готово', 'order': 3},
        ]
        for s in statuses:
            TaskStatus.objects.get_or_create(name=s['name'], defaults={'order': s['order']})
        self.stdout.write(self.style.SUCCESS('✅ Статусы задач созданы'))

        # 2. Пользователи
        user1, _ = User.objects.get_or_create(username='ivanov')
        user1.set_password('user12345')
        user1.save()

        user2, _ = User.objects.get_or_create(username='petrov')
        user2.set_password('user12345')
        user2.save()
        self.stdout.write(self.style.SUCCESS('✅ Пользователи созданы'))

        # 3. Проект
        proj_status, _ = ProjectStatus.objects.get_or_create(name='Активен')
        proj_priority, _ = Priority.objects.get_or_create(name='Средний')

        project, _ = Project.objects.get_or_create(
            name='Тестовый проект',
            defaults={
                'description': 'Проект для тестирования',
                'status': proj_status,
                'priority': proj_priority,
            }
        )
        self.stdout.write(self.style.SUCCESS('✅ Проект создан'))

        # 4. Статусы для задач
        in_progress = TaskStatus.objects.get(name='В работе')
        on_review = TaskStatus.objects.get(name='На проверке')
        done = TaskStatus.objects.get(name='Готово')

        # 5. Задачи
        Task.objects.create(
            title='Разработка API для проектов',
            description='Реализовать эндпоинты для управления проектами',
            priority='high',
            planned_end_date=timezone.now() + timezone.timedelta(days=7),
            status=in_progress,
            assigned_to=user1,
            author=user2,
            project=project,
        )
        Task.objects.create(
            title='Верстка главной страницы',
            description='Сверстать главную страницу по макету',
            priority='medium',
            planned_end_date=timezone.now() + timezone.timedelta(days=3),
            status=on_review,
            assigned_to=user1,
            author=user2,
            project=project,
        )
        Task.objects.create(
            title='Настройка базы данных',
            description='Создать структуру БД и применить миграции',
            priority='high',
            planned_end_date=timezone.now() - timezone.timedelta(days=1),
            status=done,
            assigned_to=user2,
            author=user2,
            project=project,
        )
        self.stdout.write(self.style.SUCCESS('✅ Тестовые задачи созданы'))