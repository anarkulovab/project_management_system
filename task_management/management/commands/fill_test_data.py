from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from task_management.models import TaskStatus, Task
from django.utils import timezone


class Command(BaseCommand):
    help = 'Заполнение БД тестовыми данными'

    def handle(self, *args, **kwargs):
        # 1. Создаём статусы
        statuses = [
            {'name': 'В работе', 'order': 1},
            {'name': 'На проверке', 'order': 2},
            {'name': 'Готово', 'order': 3},
        ]
        for s in statuses:
            TaskStatus.objects.get_or_create(name=s['name'], defaults={'order': s['order']})

        self.stdout.write(self.style.SUCCESS('✅ Статусы созданы'))

        # 2. Создаём пользователей
        user1, _ = User.objects.get_or_create(username='ivanov', email='ivanov@mail.ru')
        user1.set_password('user12345')
        user1.save()

        user2, _ = User.objects.get_or_create(username='petrov', email='petrov@mail.ru')
        user2.set_password('user12345')
        user2.save()

        self.stdout.write(self.style.SUCCESS('✅ Пользователи созданы'))

        # 3. Создаём задачи
        in_progress = TaskStatus.objects.get(name='В работе')
        on_review = TaskStatus.objects.get(name='На проверке')
        done = TaskStatus.objects.get(name='Готово')

        Task.objects.create(
            title='Разработка API для проектов',
            description='Реализовать эндпоинты для управления проектами',
            priority='high',
            planned_end_date=timezone.now() + timezone.timedelta(days=7),
            status=in_progress,
            assigned_to=user1,
            author=user2,
        )
        Task.objects.create(
            title='Верстка главной страницы',
            description='Сверстать главную страницу по макету',
            priority='medium',
            planned_end_date=timezone.now() + timezone.timedelta(days=3),
            status=on_review,
            assigned_to=user1,
            author=user2,
        )
        Task.objects.create(
            title='Настройка базы данных',
            description='Создать структуру БД и применить миграции',
            priority='high',
            planned_end_date=timezone.now() - timezone.timedelta(days=1),
            status=done,
            assigned_to=user2,
            author=user2,
        )

        self.stdout.write(self.style.SUCCESS('✅ Тестовые задачи созданы'))