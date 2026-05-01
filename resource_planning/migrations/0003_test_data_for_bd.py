from django.db import migrations
from django.contrib.auth.models import User


def create_roles(apps, schema_editor):
    Role = apps.get_model('resource_planning', 'Role')
    Role.objects.get_or_create(name='Директор', description='Высшее руководство компании')
    Role.objects.get_or_create(name='Руководитель проекта', description='Менеджер проектной команды')
    Role.objects.get_or_create(name='Исполнитель', description='Участник проектной команды')


def create_project_statuses(apps, schema_editor):
    ProjectStatus = apps.get_model('resource_planning', 'ProjectStatus')
    for name in ['Активен', 'Приостановлен', 'Завершён', 'Отменён']:
        ProjectStatus.objects.get_or_create(name=name)


def create_priorities(apps, schema_editor):
    Priority = apps.get_model('resource_planning', 'Priority')
    for name in ['Низкий', 'Средний', 'Высокий', 'Критический']:
        Priority.objects.get_or_create(name=name)


def create_absence_types(apps, schema_editor):
    AbsenceType = apps.get_model('resource_planning', 'AbsenceType')
    for name in ['Отпуск', 'Больничный', 'Отгул', 'Командировка']:
        AbsenceType.objects.get_or_create(name=name)


def create_probability_levels(apps, schema_editor):
    ProbabilityLevel = apps.get_model('resource_planning', 'ProbabilityLevel')
    for name in ['Низкая', 'Средняя', 'Высокая']:
        ProbabilityLevel.objects.get_or_create(name=name)


def create_impact_levels(apps, schema_editor):
    ImpactLevel = apps.get_model('resource_planning', 'ImpactLevel')
    for name in ['Низкое', 'Среднее', 'Высокое', 'Критическое']:
        ImpactLevel.objects.get_or_create(name=name)


def create_risk_statuses(apps, schema_editor):
    RiskStatus = apps.get_model('resource_planning', 'RiskStatus')
    for name in ['Выявлен', 'Анализируется', 'Приняты меры', 'Закрыт']:
        RiskStatus.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ('resource_planning', '0002_creating_all_models'),  # замените на реальную предыдущую миграцию
    ]

    operations = [
        migrations.RunPython(create_roles),
        migrations.RunPython(create_project_statuses),
        migrations.RunPython(create_priorities),
        migrations.RunPython(create_absence_types),
        migrations.RunPython(create_probability_levels),
        migrations.RunPython(create_impact_levels),
        migrations.RunPython(create_risk_statuses)
    ]