from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from resource_planning.models import Role


class Command(BaseCommand):
    help = 'Создаёт тестовых пользователей с реальными паролями'

    def handle(self, *args, **kwargs):
        director_role = Role.objects.get(name='Директор')
        manager_role = Role.objects.get(name='Руководитель проекта')
        executor_role = Role.objects.get(name='Исполнитель')

        users = [
            ('director', 'director@example.com', 'Иван', 'Директоров', director_role),
            ('manager', 'manager@example.com', 'Пётр', 'Руководителев', manager_role),
            ('executor1', 'executor1@example.com', 'Анна', 'Исполнителева', executor_role),
            ('executor2', 'executor2@example.com', 'Сергей', 'Исполнителев', executor_role),
        ]

        for username, email, first_name, last_name, role in users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'first_name': first_name, 'last_name': last_name}
            )
            if created:
                user.set_password('testpassword123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Создан пользователь: {username}'))
            else:
                self.stdout.write(self.style.WARNING(f'Пользователь уже существует: {username}'))