from django.db import models
from django.contrib.auth.models import User

# СПРАВОЧНИКИ

# 1. Роли пользователей - были удалены так как используются готовые модели django


# 2. Статусы проектов
class ProjectStatus(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название статуса")

    class Meta:
        verbose_name = "Статус проекта"
        verbose_name_plural = "Статусы проектов"

    def __str__(self):
        return self.name


# 3. Приоритеты
class Priority(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название приоритета")

    class Meta:
        verbose_name = "Приоритет"
        verbose_name_plural = "Приоритеты"

    def __str__(self):
        return self.name


# 4. Типы отсутствий сотрудников
class AbsenceType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Тип отсутствия")

    class Meta:
        verbose_name = "Тип отсутствия"
        verbose_name_plural = "Типы отсутствий"

    def __str__(self):
        return self.name

# Модуль директора
# 5. Уровни вероятности рисков
class ProbabilityLevel(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Уровень вероятности")

    class Meta:
        verbose_name = "Уровень вероятности"
        verbose_name_plural = "Уровни вероятности"

    def __str__(self):
        return self.name

# Модуль директора
# 6. Уровни влияния рисков
class ImpactLevel(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Уровень влияния")

    class Meta:
        verbose_name = "Уровень влияния"
        verbose_name_plural = "Уровни влияния"

    def __str__(self):
        return self.name

# Модуль директора
# 7. Статусы рисков
class RiskStatus(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Статус риска")

    class Meta:
        verbose_name = "Статус риска"
        verbose_name_plural = "Статусы рисков"

    def __str__(self):
        return self.name


# БИЗНЕС-СУЩНОСТИ

# 8. Проекты
class Project(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название проекта")
    description = models.TextField(blank=True, verbose_name="Описание")
    start_date_plan = models.DateField(null=True, blank=True, verbose_name="Плановая дата начала")
    end_date_plan = models.DateField(null=True, blank=True, verbose_name="Плановая дата окончания")
    start_date_fact = models.DateField(null=True, blank=True, verbose_name="Фактическая дата начала")
    end_date_fact = models.DateField(null=True, blank=True, verbose_name="Фактическая дата окончания")
    status = models.ForeignKey(ProjectStatus, on_delete=models.PROTECT, verbose_name="Статус")
    priority = models.ForeignKey(Priority, on_delete=models.PROTECT, verbose_name="Приоритет")
    manager = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='managed_projects', verbose_name="Руководитель"
    )
    participants = models.ManyToManyField(
        User, related_name='participating_projects', blank=True, verbose_name="Участники"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")

    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"
        ordering = ['-created_at']

    def __str__(self):
        return self.name


# 9. Назначения на задачи
class TaskAssignment(models.Model):
    task = models.ForeignKey(
        'task_management.Task',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name="Задача"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='assignments', verbose_name="Исполнитель"
    )
    planned_hours = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, verbose_name="Плановые часы"
    )
    actual_hours = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, verbose_name="Фактические часы"
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата назначения")

    class Meta:
        verbose_name = "Назначение на задачу"
        verbose_name_plural = "Назначения на задачи"
        unique_together = ['task', 'user']

    def __str__(self):
        return f"{self.user} → {self.task}"


# 10. Отсутствия сотрудников
class UserAbsence(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='absences', verbose_name="Сотрудник"
    )
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    absence_type = models.ForeignKey(
        AbsenceType, on_delete=models.PROTECT, verbose_name="Тип отсутствия"
    )
    reason = models.TextField(blank=True, verbose_name="Причина")

    class Meta:
        verbose_name = "Отсутствие сотрудника"
        verbose_name_plural = "Отсутствия сотрудников"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.user} — {self.absence_type} ({self.start_date} – {self.end_date})"


# Модуль директора
# 11. Риски
class Risk(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='risks', verbose_name="Проект"
    )
    task = models.ForeignKey(
        'task_management.Task',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='risks',
        verbose_name="Связанная задача"
    )
    title = models.CharField(max_length=255, verbose_name="Название риска")
    description = models.TextField(blank=True, verbose_name="Описание")
    probability = models.ForeignKey(
        ProbabilityLevel, on_delete=models.PROTECT, verbose_name="Вероятность"
    )
    impact = models.ForeignKey(
        ImpactLevel, on_delete=models.PROTECT, verbose_name="Степень влияния"
    )
    status = models.ForeignKey(
        RiskStatus, on_delete=models.PROTECT, verbose_name="Статус риска"
    )
    responsible = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='responsible_risks', verbose_name="Ответственный"
    )
    mitigation_plan = models.TextField(blank=True, verbose_name="План реагирования")
    identified_at = models.DateField(auto_now_add=True, verbose_name="Дата выявления")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")

    class Meta:
        verbose_name = "Риск"
        verbose_name_plural = "Риски"
        ordering = ['-identified_at']

    def __str__(self):
        return self.title


# Модуль директора
# 12. История изменений рисков
class RiskHistory(models.Model):
    risk = models.ForeignKey(
        Risk, on_delete=models.CASCADE, related_name='history', verbose_name="Риск"
    )
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Пользователь"
    )
    old_status = models.ForeignKey(
        RiskStatus, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='old_status_history', verbose_name="Старый статус"
    )
    new_status = models.ForeignKey(
        RiskStatus, on_delete=models.PROTECT,
        related_name='new_status_history', verbose_name="Новый статус"
    )
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Время изменения")

    class Meta:
        verbose_name = "История изменения риска"
        verbose_name_plural = "История изменений рисков"
        ordering = ['-changed_at']

    def __str__(self):
        return f"Риск {self.risk}: {self.old_status} → {self.new_status}"

# Модуль директора
# 13. Бюджеты проектов
class Budget(models.Model):
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name='budget', verbose_name="Проект"
    )
    planned_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Плановая сумма"
    )
    actual_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Фактическая сумма"
    )
    approved_at = models.DateField(null=True, blank=True, verbose_name="Дата утверждения")
    notes = models.TextField(blank=True, verbose_name="Примечания")

    class Meta:
        verbose_name = "Бюджет проекта"
        verbose_name_plural = "Бюджеты проектов"

    def __str__(self):
        return f"Бюджет проекта: {self.project.name}"


# 14. KPI показатели
class KPI(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='kpis', verbose_name="Проект"
    )
    name = models.CharField(max_length=255, verbose_name="Название показателя")
    value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Значение"
    )
    calculated_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата расчёта")

    class Meta:
        verbose_name = "KPI показатель"
        verbose_name_plural = "KPI показатели"
        ordering = ['-calculated_at']

    def __str__(self):
        return f"{self.name} = {self.value} ({self.project.name})"

# 15. СВЯЗЬ РУКОВОДИТЕЛЬ — ИСПОЛНИТЕЛИ
class Employee(models.Model):
    manager = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subordinates',
        verbose_name="Руководитель"
    )
    employee = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='manager_relation',
        verbose_name="Сотрудник"
    )
    weekly_work_hours = models.PositiveSmallIntegerField(
        default=40,
        verbose_name="Норма часов в неделю")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        verbose_name = "Сотрудник руководителя"
        verbose_name_plural = "Сотрудники руководителя"
        unique_together = ['manager', 'employee']

    def __str__(self):
        return f"{self.employee.get_full_name() or self.employee.username} → руководитель: {self.manager.get_full_name() or self.manager.username}"