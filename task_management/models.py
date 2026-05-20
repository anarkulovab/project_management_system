# task_management/models.py
from django.db import models
from django.contrib.auth.models import User


# -----------------------------------------------------------
# 1. СТАТУСЫ ЗАДАЧ (таблица №5)
# -----------------------------------------------------------
class TaskStatus(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Название статуса")
    order = models.IntegerField(default=0, verbose_name="Порядок отображения")

    class Meta:
        verbose_name = "Статус задачи"
        verbose_name_plural = "Статусы задач"
        ordering = ['order']

    def __str__(self):
        return self.name


# -----------------------------------------------------------
# 2. ЗАДАЧИ (таблица №2)
# -----------------------------------------------------------
class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('critical', 'Критический'),
    ]

    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name="Приоритет")
    planned_end_date = models.DateTimeField(verbose_name="Плановый срок")
    planned_start_date = models.DateTimeField(null=True, blank=True, verbose_name="Плановое начало")

    # Связь с проектом пока закомментирована — ждём модель от Бегимай
    project = models.ForeignKey(
        'resource_planning.Project',
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Проект"
    )
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtasks',
        verbose_name="Родительская задача"
    )
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_tasks', verbose_name="Исполнитель")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_tasks',
                               verbose_name="Автор")
    status = models.ForeignKey(TaskStatus, on_delete=models.SET_NULL, null=True, verbose_name="Статус")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# -----------------------------------------------------------
# 3. КОММЕНТАРИИ (таблица №7)
# -----------------------------------------------------------
class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments', verbose_name="Задача")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Автор")
    text = models.TextField(verbose_name="Текст комментария")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ['created_at']

    def __str__(self):
        return f"Комментарий от {self.author} к {self.task}"


# -----------------------------------------------------------
# 4. ИСТОРИЯ ИЗМЕНЕНИЙ (таблица №8)
# -----------------------------------------------------------
class TaskHistory(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history', verbose_name="Задача")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Пользователь")
    changed_field = models.CharField(max_length=100, verbose_name="Изменённое поле")
    old_value = models.CharField(max_length=255, blank=True, verbose_name="Старое значение")
    new_value = models.CharField(max_length=255, blank=True, verbose_name="Новое значение")
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Время изменения")

    class Meta:
        verbose_name = "История изменения"
        verbose_name_plural = "История изменений"
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.changed_at}: {self.user} изменил {self.changed_field} у {self.task}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ExecutorChangeRequest(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='change_requests')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    reason = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']