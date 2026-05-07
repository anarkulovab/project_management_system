import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import date, timedelta
from resource_planning.models import (
    ProjectStatus, Priority, AbsenceType,
    ProbabilityLevel, ImpactLevel, RiskStatus,
    Project, TaskAssignment, UserAbsence,
    Risk, RiskHistory, Budget, KPI, Employee
)
from task_management.models import Task, TaskStatus

# ---------------------------------------------------
# 1. СПРАВОЧНИКИ
# ---------------------------------------------------

print('Создаю справочники...')

status_active, _ = ProjectStatus.objects.get_or_create(name='Активен')
status_paused, _ = ProjectStatus.objects.get_or_create(name='Приостановлен')
status_completed, _ = ProjectStatus.objects.get_or_create(name='Завершён')
status_cancelled, _ = ProjectStatus.objects.get_or_create(name='Отменён')

pr_low, _ = Priority.objects.get_or_create(name='Низкий')
pr_medium, _ = Priority.objects.get_or_create(name='Средний')
pr_high, _ = Priority.objects.get_or_create(name='Высокий')
pr_critical, _ = Priority.objects.get_or_create(name='Критический')

abs_vacation, _ = AbsenceType.objects.get_or_create(name='Отпуск')
abs_sick, _ = AbsenceType.objects.get_or_create(name='Больничный')
abs_dayoff, _ = AbsenceType.objects.get_or_create(name='Отгул')
abs_trip, _ = AbsenceType.objects.get_or_create(name='Командировка')

prob_low, _ = ProbabilityLevel.objects.get_or_create(name='Низкая')
prob_medium, _ = ProbabilityLevel.objects.get_or_create(name='Средняя')
prob_high, _ = ProbabilityLevel.objects.get_or_create(name='Высокая')

imp_low, _ = ImpactLevel.objects.get_or_create(name='Низкое')
imp_medium, _ = ImpactLevel.objects.get_or_create(name='Среднее')
imp_high, _ = ImpactLevel.objects.get_or_create(name='Высокое')
imp_critical, _ = ImpactLevel.objects.get_or_create(name='Критическое')

risk_new, _ = RiskStatus.objects.get_or_create(name='Выявлен')
risk_analysis, _ = RiskStatus.objects.get_or_create(name='Анализируется')
risk_mitigated, _ = RiskStatus.objects.get_or_create(name='Приняты меры')
risk_closed, _ = RiskStatus.objects.get_or_create(name='Закрыт')

# Статусы задач — создаём полный набор
ts_planned, _ = TaskStatus.objects.get_or_create(name='Запланирована', defaults={'order': 1})
ts_new, _ = TaskStatus.objects.get_or_create(name='Новая', defaults={'order': 2})
ts_in_progress, _ = TaskStatus.objects.get_or_create(name='В работе', defaults={'order': 3})
ts_review, _ = TaskStatus.objects.get_or_create(name='На проверке', defaults={'order': 4})
ts_done, _ = TaskStatus.objects.get_or_create(name='Готово', defaults={'order': 5})

manager_group, _ = Group.objects.get_or_create(name='Руководитель проекта')
executor_group, _ = Group.objects.get_or_create(name='Исполнитель')
director_group, _ = Group.objects.get_or_create(name='Директор')

print('✓ Справочники созданы')

# ---------------------------------------------------
# 2. ПОЛЬЗОВАТЕЛИ
# ---------------------------------------------------

print('Создаю пользователей...')

users_data = [
    ('director', 'director@example.com', 'Илья', 'Новиков', [manager_group]),
    ('manager', 'manager@example.com', 'Марина', 'Васильева', [manager_group]),
    ('executor1', 'executor1@example.com', 'Анна', 'Петрова', [executor_group]),
    ('executor2', 'executor2@example.com', 'Сергей', 'Смирной', [executor_group]),
]

created = {}
for username, email, first_name, last_name, groups in users_data:
    user, is_new = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'first_name': first_name, 'last_name': last_name}
    )
    if is_new:
        user.set_password('testpassword123')
        user.save()
    user.groups.set(groups)
    created[username] = user

director = created['director']
manager = created['manager']
executor1 = created['executor1']
executor2 = created['executor2']

print('✓ Пользователи созданы')

# ---------------------------------------------------
# 3. СВЯЗЬ РУКОВОДИТЕЛЬ — ИСПОЛНИТЕЛИ
# ---------------------------------------------------

Employee.objects.get_or_create(manager=manager, employee=executor1)
Employee.objects.get_or_create(manager=manager, employee=executor2)
print('✓ Связи руководитель-исполнители созданы')

# ---------------------------------------------------
# 4. ПРОЕКТЫ
# ---------------------------------------------------

print('Создаю проекты...')

p1, _ = Project.objects.get_or_create(
    name='Разработка CRM-системы',
    defaults={
        'description': 'Создание системы для управления взаимоотношениями с клиентами',
        'start_date_plan': date(2026, 1, 15),
        'end_date_plan': date(2026, 6, 30),
        'start_date_fact': date(2026, 1, 20),
        'status': status_active,
        'priority': pr_high,
        'manager': manager,
    }
)

p2, _ = Project.objects.get_or_create(
    name='Внедрение ERP-модуля',
    defaults={
        'description': 'Интеграция модуля управления ресурсами предприятия',
        'start_date_plan': date(2026, 2, 1),
        'end_date_plan': date(2026, 5, 15),
        'start_date_fact': date(2026, 2, 1),
        'end_date_fact': date(2026, 5, 20),
        'status': status_completed,
        'priority': pr_critical,
        'manager': manager,
    }
)

p3, _ = Project.objects.get_or_create(
    name='Мобильное приложение',
    defaults={
        'description': 'Разработка приложения для iOS и Android',
        'start_date_plan': date(2026, 3, 1),
        'end_date_plan': date(2026, 8, 1),
        'status': status_active,
        'priority': pr_medium,
        'manager': manager,
    }
)

p1.participants.add(executor1, executor2)
p2.participants.add(executor1)
p3.participants.add(executor1, executor2)

print('✓ Проекты созданы')

# ---------------------------------------------------
# 5. ЗАДАЧИ
# ---------------------------------------------------

print('Создаю задачи...')

t1_1 = Task.objects.create(
    title='Разработка архитектуры CRM',
    project=p1, description='Спроектировать модульную архитектуру системы',
    priority='high', planned_start_date=timezone.now() - timedelta(days=60),
    planned_end_date=timezone.now() - timedelta(days=30),
    assigned_to=executor1, author=manager, status=ts_done
)

t1_2 = Task.objects.create(
    title='Создание интерфейса CRM',
    project=p1, description='Разработать UI для менеджеров по продажам',
    priority='high', planned_start_date=timezone.now() - timedelta(days=30),
    planned_end_date=timezone.now() + timedelta(days=15),
    assigned_to=executor2, author=manager, status=ts_in_progress
)

t1_3 = Task.objects.create(
    title='Тестирование CRM',
    project=p1, description='Провести функциональное и нагрузочное тестирование',
    priority='medium', planned_start_date=timezone.now() - timedelta(days=10),
    planned_end_date=timezone.now() + timedelta(days=30),
    assigned_to=executor1, author=manager, status=ts_review
)

t2_1 = Task.objects.create(
    title='Настройка ERP-модуля',
    project=p2, description='Адаптировать ERP под бизнес-процессы компании',
    priority='critical', planned_start_date=timezone.now() - timedelta(days=90),
    planned_end_date=timezone.now() - timedelta(days=45),
    assigned_to=executor1, author=manager, status=ts_done
)

t3_1 = Task.objects.create(
    title='Дизайн мобильного приложения',
    project=p3, description='Разработать макеты всех экранов',
    priority='medium', planned_start_date=timezone.now() - timedelta(days=15),
    planned_end_date=timezone.now() + timedelta(days=5),
    assigned_to=executor2, author=manager, status=ts_in_progress
)

t3_2 = Task.objects.create(
    title='Разработка API для приложения',
    project=p3, description='Создать REST API для мобильного клиента',
    priority='high', planned_start_date=timezone.now() + timedelta(days=5),
    planned_end_date=timezone.now() + timedelta(days=55),
    assigned_to=executor1, author=manager, status=ts_new
)

print('✓ Задачи созданы')

# ---------------------------------------------------
# 6. НАЗНАЧЕНИЯ
# ---------------------------------------------------

print('Создаю назначения...')

assignments = [
    (t1_1, executor1, 40, 38),
    (t1_2, executor2, 60, 25),
    (t1_3, executor1, 80, 0),
    (t2_1, executor1, 120, 115),
    (t3_1, executor2, 40, 10),
    (t3_2, executor1, 100, 0),
]

for task, user, planned, actual in assignments:
    TaskAssignment.objects.get_or_create(
        task=task, user=user,
        defaults={'planned_hours': planned, 'actual_hours': actual, 'assigned_at': timezone.now()}
    )

print('✓ Назначения созданы')

# ---------------------------------------------------
# 7. КPI
# ---------------------------------------------------

print('Создаю KPI...')

kpi_data = [
    (p1, 'Процент выполнения', 45.00),
    (p1, 'Индекс соблюдения сроков', 0.85),
    (p1, 'Утилизация ресурсов', 72.50),
    (p2, 'Процент выполнения', 100.00),
    (p2, 'Индекс соблюдения сроков', 0.95),
    (p3, 'Процент выполнения', 20.00),
    (p3, 'Индекс соблюдения сроков', 0.70),
    (p3, 'Утилизация ресурсов', 55.00),
]

for project, name, value in kpi_data:
    KPI.objects.get_or_create(project=project, name=name, defaults={'value': value})

print('✓ KPI созданы')

# ---------------------------------------------------
# 8. РИСКИ
# ---------------------------------------------------

print('Создаю риски...')

risk1, _ = Risk.objects.get_or_create(
    title='Уход ключевого разработчика',
    defaults={
        'project': p1,
        'task': t1_1,
        'description': 'Ведущий разработчик может покинуть проект',
        'probability': prob_medium,
        'impact': imp_high,
        'status': risk_analysis,
        'responsible': manager,
        'mitigation_plan': 'Подготовить второго сотрудника, документация передана',
        'identified_at': date(2026, 2, 1),
    }
)

risk2, _ = Risk.objects.get_or_create(
    title='Задержка поставки оборудования',
    defaults={
        'project': p1,
        'description': 'Серверное оборудование может быть задержано поставщиком',
        'probability': prob_low,
        'impact': imp_medium,
        'status': risk_new,
        'responsible': manager,
        'mitigation_plan': 'Поиск альтернативных поставщиков',
        'identified_at': date(2026, 2, 10),
    }
)

risk3, _ = Risk.objects.get_or_create(
    title='Превышение бюджета',
    defaults={
        'project': p3,
        'description': 'Расходы могут превысить плановый бюджет',
        'probability': prob_high,
        'impact': imp_critical,
        'status': risk_analysis,
        'responsible': manager,
        'mitigation_plan': 'Еженедельный мониторинг расходов',
        'identified_at': date(2026, 3, 1),
    }
)

risk4, _ = Risk.objects.get_or_create(
    title='Недостаток компетенций команды',
    defaults={
        'project': p3,
        'description': 'Команда не имеет опыта разработки мобильных приложений',
        'probability': prob_high,
        'impact': imp_high,
        'status': risk_analysis,
        'responsible': manager,
        'mitigation_plan': 'Провести обучение, нанять консультанта',
        'identified_at': date(2026, 3, 5),
    }
)

print('✓ Риски созданы')

# ---------------------------------------------------
# 9. ИСТОРИЯ ИЗМЕНЕНИЙ РИСКОВ
# ---------------------------------------------------

print('Создаю историю рисков...')

RiskHistory.objects.get_or_create(
    risk=risk1,
    defaults={
        'user': manager,
        'old_status': risk_new,
        'new_status': risk_analysis,
        'comment': 'Начат анализ риска, назначен ответственный',
        'changed_at': timezone.now(),
    }
)

RiskHistory.objects.get_or_create(
    risk=risk3,
    defaults={
        'user': manager,
        'old_status': risk_new,
        'new_status': risk_analysis,
        'comment': 'Риск взят в работу, определён план реагирования',
        'changed_at': timezone.now(),
    }
)

print('✓ История рисков создана')

# ---------------------------------------------------
# 10. ОТСУТСТВИЯ СОТРУДНИКОВ
# ---------------------------------------------------

print('Создаю отсутствия...')

UserAbsence.objects.get_or_create(
    user=executor1,
    start_date=date(2026, 4, 10),
    defaults={
        'end_date': date(2026, 4, 24),
        'absence_type': abs_vacation,
        'reason': 'Ежегодный оплачиваемый отпуск',
    }
)

UserAbsence.objects.get_or_create(
    user=executor2,
    start_date=date(2026, 5, 5),
    defaults={
        'end_date': date(2026, 5, 8),
        'absence_type': abs_sick,
        'reason': 'ОРВИ',
    }
)

print('✓ Отсутствия созданы')

# ---------------------------------------------------
# 11. БЮДЖЕТЫ ПРОЕКТОВ
# ---------------------------------------------------

print('Создаю бюджеты...')

budgets_data = [
    (p1, 1500000, 1200000, date(2026, 1, 10)),
    (p2, 800000, 800000, date(2026, 1, 25)),
    (p3, 2000000, 600000, date(2026, 2, 15)),
]

for project, planned, actual, approved in budgets_data:
    Budget.objects.get_or_create(
        project=project,
        defaults={
            'planned_amount': planned,
            'actual_amount': actual,
            'approved_at': approved,
        }
    )

print('✓ Бюджеты созданы')

# ---------------------------------------------------
# ГОТОВО
# ---------------------------------------------------
print('=' * 50)
print('БАЗА ДАННЫХ УСПЕШНО ЗАПОЛНЕНА')
print('=' * 50)
print()
print('Пользователи для входа:')
print('  manager   / testpassword123  (руководитель)')
print('  executor1 / testpassword123  (исполнитель)')
print('  executor2 / testpassword123  (исполнитель)')
print('  director  / testpassword123  (директор)')