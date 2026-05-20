import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import date, timedelta, datetime
from resource_planning.models import (
    ProjectStatus, Priority, AbsenceType,
    ProbabilityLevel, ImpactLevel, RiskStatus,
    Project, TaskAssignment, UserAbsence,
    Risk, RiskHistory, Budget, KPI, Employee
)
from task_management.models import Task, TaskStatus, Comment, Notification

# ---------------------------------------------------
# 0. ОЧИСТКА ПЕРЕД ЗАПОЛНЕНИЕМ
# ---------------------------------------------------

print('Очищаю старые данные...')

from task_management.models import Comment, Notification, TaskHistory
from resource_planning.models import RiskHistory, Risk, Budget

# Удаляем в порядке зависимости
Task.objects.filter(parent_task__isnull=False).delete()
TaskHistory.objects.all().delete()
Comment.objects.all().delete()
Notification.objects.all().delete()
TaskAssignment.objects.all().delete()
RiskHistory.objects.all().delete()
Risk.objects.all().delete()
Budget.objects.all().delete()
KPI.objects.all().delete()
UserAbsence.objects.all().delete()
Task.objects.all().delete()
Project.objects.all().delete()
Employee.objects.all().delete()
User.objects.filter(is_superuser=False).delete()

print('✓ Старые данные удалены')

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
    # Для Насти
    ('director', 'director@example.com', 'Илья', 'Новиков', [director_group]),
    # Руководители (два — для проверки изоляции данных)
    ('marina.vasilyeva', 'marina@example.com', 'Марина', 'Васильева', [manager_group]),
    ('alexey.fedorov', 'alexey@example.com', 'Алексей', 'Фёдоров', [manager_group]),
    # Исполнители
    ('anna.petrova', 'anna@example.com', 'Анна', 'Петрова', [executor_group]),
    ('sergey.smirnov', 'sergey@example.com', 'Сергей', 'Смирнов', [executor_group]),
    ('dmitry.volkov', 'dmitry@example.com', 'Дмитрий', 'Волков', [executor_group]),
    ('elena.sokolova', 'elena@example.com', 'Елена', 'Соколова', [executor_group]),
    # Исполнитель без руководителя (для Насти)
    ('nikolay.ustinov', 'nikolay@example.com', 'Николай', 'Устинов', [executor_group]),
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
manager = created['marina.vasilyeva']
manager2 = created['alexey.fedorov']
executor1 = created['anna.petrova']
executor2 = created['sergey.smirnov']
executor3 = created['dmitry.volkov']
executor4 = created['elena.sokolova']
executor_no_manager = created['nikolay.ustinov']

print('✓ Пользователи созданы')

# ---------------------------------------------------
# 3. СВЯЗЬ РУКОВОДИТЕЛЬ — ИСПОЛНИТЕЛИ
# ---------------------------------------------------

for emp in [executor1, executor2, executor3, executor4]:
    Employee.objects.get_or_create(
        employee=emp,
        defaults={'manager': manager}
    )

print('✓ Связи руководитель-исполнители созданы')

# ---------------------------------------------------
# 4. ПРОЕКТЫ
# ---------------------------------------------------

print('Создаю проекты...')

# Проекты Марины
p1, _ = Project.objects.get_or_create(
    name='Внедрение CRM-системы',
    defaults={
        'description': 'Автоматизация работы отдела продаж и клиентского сервиса',
        'start_date_plan': date(2026, 4, 1),
        'end_date_plan': date(2026, 7, 30),
        'start_date_fact': date(2026, 4, 5),
        'status': status_active,
        'priority': pr_high,
        'manager': manager,
    }
)

p2, _ = Project.objects.get_or_create(
    name='Мобильное приложение',
    defaults={
        'description': 'Разработка нативного приложения для iOS и Android',
        'start_date_plan': date(2026, 5, 1),
        'end_date_plan': date(2026, 9, 15),
        'status': status_active,
        'priority': pr_high,
        'manager': manager,
    }
)

p3, _ = Project.objects.get_or_create(
    name='Корпоративный портал',
    defaults={
        'description': 'Единая точка входа для всех внутренних сервисов компании',
        'start_date_plan': date(2026, 5, 15),
        'end_date_plan': date(2026, 8, 30),
        'status': status_active,
        'priority': pr_medium,
        'manager': manager,
    }
)

# Для Насти: проект с перерасходом бюджета
p4, _ = Project.objects.get_or_create(
    name='Система аналитики продаж',
    defaults={
        'description': 'Внедрение BI-инструментов для анализа эффективности',
        'start_date_plan': date(2026, 1, 10),
        'end_date_plan': date(2026, 4, 30),
        'start_date_fact': date(2026, 1, 15),
        'status': status_active,
        'priority': pr_critical,
        'manager': manager,
    }
)

# Для Насти: проект с просроченным сроком
p5, _ = Project.objects.get_or_create(
    name='Обновление инфраструктуры',
    defaults={
        'description': 'Модернизация серверного оборудования и сети',
        'start_date_plan': date(2026, 2, 1),
        'end_date_plan': date(2026, 4, 15),
        'start_date_fact': date(2026, 2, 5),
        'status': status_paused,
        'priority': pr_high,
        'manager': manager,
    }
)

# Для Насти: пустой проект
p6, _ = Project.objects.get_or_create(
    name='Чат-бот для поддержки',
    defaults={
        'description': 'Разработка бота для автоматизации ответов клиентам',
        'start_date_plan': date(2026, 7, 1),
        'end_date_plan': date(2026, 10, 1),
        'status': status_active,
        'priority': pr_low,
        'manager': manager,
    }
)

# Проект второго руководителя (для проверки изоляции)
p7, _ = Project.objects.get_or_create(
    name='Внутренний аудит ИТ-систем',
    defaults={
        'description': 'Комплексная проверка безопасности и отказоустойчивости',
        'start_date_plan': date(2026, 5, 1),
        'end_date_plan': date(2026, 6, 30),
        'status': status_active,
        'priority': pr_medium,
        'manager': manager2,
    }
)

# Участники проектов
p1.participants.add(executor1, executor2, executor3, executor4)
p2.participants.add(executor1, executor2, executor3)
p3.participants.add(executor2, executor3, executor4)
p4.participants.add(executor1, executor2)
p5.participants.add(executor1, executor3)
p7.participants.add(executor2)

print('✓ Проекты созданы')

# ---------------------------------------------------
# 5. ЗАДАЧИ
# ---------------------------------------------------

print('Создаю задачи...')

now = timezone.now()

# --- Задачи для Анны Петровой (CRM) ---
task_anna_1 = Task.objects.create(
    title='Разработка модуля контактов', project=p1,
    description='CRUD-операции для управления контактами клиентов',
    priority='high', planned_start_date=now - timedelta(days=14),
    planned_end_date=now + timedelta(days=7),
    assigned_to=executor1, author=manager, status=ts_in_progress
)
task_anna_2 = Task.objects.create(
    title='Интеграция с 1С', project=p1,
    description='Настройка обмена данными между CRM и учётной системой',
    priority='critical', planned_start_date=now - timedelta(days=10),
    planned_end_date=now - timedelta(days=1),
    assigned_to=executor1, author=manager, status=ts_review
)
task_anna_3 = Task.objects.create(
    title='Дашборд для руководителя', project=p1,
    description='Аналитическая панель с графиками по продажам',
    priority='medium', planned_start_date=now + timedelta(days=3),
    planned_end_date=now + timedelta(days=20),
    assigned_to=executor1, author=manager, status=ts_new
)
task_anna_4 = Task.objects.create(
    title='Обучение сотрудников', project=p1,
    description='Провести тренинг по работе с новой CRM',
    priority='medium', planned_start_date=now + timedelta(days=14),
    planned_end_date=now + timedelta(days=16),
    assigned_to=executor1, author=manager, status=ts_planned
)
task_anna_5 = Task.objects.create(
    title='Миграция данных из Excel', project=p1,
    description='Перенос клиентской базы из старых таблиц в CRM',
    priority='high', planned_start_date=now - timedelta(days=7),
    planned_end_date=now - timedelta(days=1),  # просрочена (срок вчера)
    assigned_to=executor1, author=manager, status=ts_in_progress
)
task_anna_6 = Task.objects.create(
    title='Настройка почтовых уведомлений', project=p1,
    description='Автоматические письма клиентам при изменении статуса сделки',
    priority='medium', planned_start_date=now - timedelta(days=21),
    planned_end_date=now - timedelta(days=5),
    assigned_to=executor1, author=manager, status=ts_done
)

# Подзадачи для «Миграция данных из Excel»
sub_1 = Task.objects.create(
    title='Проверить дубликаты', project=p1,
    description='Найти и удалить повторяющиеся записи клиентов',
    priority='high', planned_start_date=now - timedelta(days=5),
    planned_end_date=now - timedelta(days=3),
    assigned_to=executor1, author=manager, status=ts_done,
    parent_task=task_anna_5
)
sub_2 = Task.objects.create(
    title='Согласовать формат импорта', project=p1,
    description='Утвердить структуру CSV-файла с заказчиком',
    priority='medium', planned_start_date=now - timedelta(days=3),
    planned_end_date=now + timedelta(days=2),
    assigned_to=executor1, author=manager, status=ts_new,
    parent_task=task_anna_5
)
sub_3 = Task.objects.create(
    title='Написать скрипт валидации', project=p1,
    description='Скрипт проверки корректности данных перед импортом',
    priority='high', planned_start_date=now + timedelta(days=2),
    planned_end_date=now + timedelta(days=5),
    assigned_to=executor1, author=manager, status=ts_new,
    parent_task=task_anna_5
)

# --- Задачи для Сергея Смирнова ---
task_sergey_1 = Task.objects.create(
    title='Дизайн корпоративного портала', project=p3,
    description='Разработать макеты всех страниц портала',
    priority='high', planned_start_date=now - timedelta(days=10),
    planned_end_date=now + timedelta(days=10),
    assigned_to=executor2, author=manager, status=ts_in_progress
)
task_sergey_2 = Task.objects.create(
    title='Дизайн мобильного приложения', project=p2,
    description='Макеты экранов для iOS и Android',
    priority='medium', planned_start_date=now + timedelta(days=5),
    planned_end_date=now + timedelta(days=25),
    assigned_to=executor2, author=manager, status=ts_new
)
task_sergey_3 = Task.objects.create(
    title='Анимация переходов', project=p2,
    description='Проработка микроанимаций между экранами приложения',
    priority='low', planned_start_date=now - timedelta(days=3),
    planned_end_date=now + timedelta(days=7),
    assigned_to=executor2, author=manager, status=ts_in_progress
)
task_sergey_4 = Task.objects.create(
    title='Иконки приложения', project=p2,
    description='Разработать набор иконок для всех разделов',
    priority='medium', planned_start_date=now + timedelta(days=10),
    planned_end_date=now + timedelta(days=17),
    assigned_to=executor2, author=manager, status=ts_planned
)

# --- Задачи для Дмитрия Волкова ---
task_dmitry_1 = Task.objects.create(
    title='Разработка API', project=p2,
    description='REST API для мобильного клиента',
    priority='high', planned_start_date=now - timedelta(days=5),
    planned_end_date=now + timedelta(days=15),
    assigned_to=executor3, author=manager, status=ts_in_progress
)
task_dmitry_2 = Task.objects.create(
    title='Тестирование API', project=p2,
    description='Написание и прогон автотестов',
    priority='medium', planned_start_date=now + timedelta(days=16),
    planned_end_date=now + timedelta(days=25),
    assigned_to=executor3, author=manager, status=ts_new
)
task_dmitry_3 = Task.objects.create(
    title='Документация для разработчиков', project=p1,
    description='Описание архитектуры CRM и инструкции по развёртыванию',
    priority='low', planned_start_date=now + timedelta(days=7),
    planned_end_date=now + timedelta(days=14),
    assigned_to=executor3, author=manager, status=ts_planned
)
task_dmitry_4 = Task.objects.create(
    title='Рефакторинг старого кода', project=p3,
    description='Приведение легаси-модулей портала к общим стандартам',
    priority='medium', planned_start_date=now + timedelta(days=3),
    planned_end_date=now + timedelta(days=14),
    assigned_to=executor3, author=manager, status=ts_new
)

# --- Задачи для Елены Соколовой ---
task_elena_1 = Task.objects.create(
    title='Верстка главной страницы', project=p3,
    description='Адаптивная вёрстка главной страницы портала по макетам',
    priority='high', planned_start_date=now - timedelta(days=7),
    planned_end_date=now + timedelta(days=5),
    assigned_to=executor4, author=manager, status=ts_in_progress
)
task_elena_2 = Task.objects.create(
    title='Верстка личного кабинета', project=p3,
    description='Страница профиля сотрудника с настройками',
    priority='high', planned_start_date=now - timedelta(days=5),
    planned_end_date=now - timedelta(days=1),
    assigned_to=executor4, author=manager, status=ts_review
)
task_elena_3 = Task.objects.create(
    title='Адаптив под мобильные', project=p3,
    description='Адаптация всех страниц портала под планшеты и смартфоны',
    priority='medium', planned_start_date=now + timedelta(days=5),
    planned_end_date=now + timedelta(days=15),
    assigned_to=executor4, author=manager, status=ts_new
)
task_elena_4 = Task.objects.create(
    title='Тестирование верстки', project=p3,
    description='Кроссбраузерное тестирование и исправление багов',
    priority='low', planned_start_date=now + timedelta(days=16),
    planned_end_date=now + timedelta(days=20),
    assigned_to=executor4, author=manager, status=ts_planned
)

# --- Задача для второго руководителя ---
Task.objects.create(
    title='Проверка безопасности серверов', project=p7,
    description='Аудит конфигурации и прав доступа',
    priority='high', planned_start_date=now - timedelta(days=3),
    planned_end_date=now + timedelta(days=10),
    assigned_to=executor2, author=manager2, status=ts_in_progress
)

# --- Просроченная задача (для Насти) ---
Task.objects.create(
    title='Настройка BI-дашбордов', project=p4,
    description='Подключение источников данных и настройка визуализаций',
    priority='critical', planned_start_date=now - timedelta(days=30),
    planned_end_date=now - timedelta(days=5),
    assigned_to=executor1, author=manager, status=ts_in_progress
)

print('✓ Задачи созданы')

# ---------------------------------------------------
# 6. НАЗНАЧЕНИЯ (плановые и фактические часы)
# ---------------------------------------------------

print('Создаю назначения...')

assignments_data = [
    (task_anna_1, executor1, 32, 18),
    (task_anna_2, executor1, 24, 22),
    (task_anna_3, executor1, 40, 0),
    (task_anna_4, executor1, 8, 0),
    (task_anna_5, executor1, 16, 10),
    (task_anna_6, executor1, 8, 8),
    (sub_1, executor1, 4, 4),
    (sub_2, executor1, 6, 0),
    (sub_3, executor1, 8, 0),
    (task_sergey_1, executor2, 40, 22),
    (task_sergey_2, executor2, 60, 0),
    (task_sergey_3, executor2, 16, 8),
    (task_sergey_4, executor2, 12, 0),
    (task_dmitry_1, executor3, 40, 16),
    (task_dmitry_2, executor3, 30, 0),
    (task_dmitry_3, executor3, 12, 0),
    (task_dmitry_4, executor3, 24, 0),
    (task_elena_1, executor4, 32, 20),
    (task_elena_2, executor4, 20, 14),
    (task_elena_3, executor4, 30, 0),
    (task_elena_4, executor4, 12, 0),
]

for task, user, planned, actual in assignments_data:
    TaskAssignment.objects.get_or_create(
        task=task, user=user,
        defaults={'planned_hours': planned, 'actual_hours': actual, 'assigned_at': timezone.now()}
    )

print('✓ Назначения созданы')

# ---------------------------------------------------
# 7. КОММЕНТАРИИ
# ---------------------------------------------------

print('Создаю комментарии...')

Comment.objects.get_or_create(
    task=task_anna_2, author=executor1,
    defaults={'text': 'Интеграция настроена, проверила на тестовых данных. Жду проверки.'}
)
Comment.objects.get_or_create(
    task=task_anna_2, author=manager,
    defaults={'text': 'Принято, но нужно добавить обработку ошибок при таймауте.'}
)
Comment.objects.get_or_create(
    task=task_sergey_1, author=executor2,
    defaults={'text': 'Макеты готовы, загрузил в Figma. Жду согласования.'}
)
Comment.objects.get_or_create(
    task=task_elena_1, author=executor4,
    defaults={'text': 'Возникли сложности с сеткой, нужно больше времени.'}
)

print('✓ Комментарии созданы')

# ---------------------------------------------------
# 8. ОПОВЕЩЕНИЯ
# ---------------------------------------------------

print('Создаю оповещения...')

Notification.objects.get_or_create(
    user=manager, task=task_anna_2,
    defaults={'message': 'Анна Петрова перевела задачу «Интеграция с 1С» в статус «На проверке».'}
)
Notification.objects.get_or_create(
    user=executor1, task=task_anna_2,
    defaults={'message': 'Руководитель оставила комментарий к задаче «Интеграция с 1С».'}
)
Notification.objects.get_or_create(
    user=manager, task=task_elena_2,
    defaults={'message': 'Елена Соколова перевела задачу «Верстка личного кабинета» в статус «На проверке».'}
)
Notification.objects.get_or_create(
    user=executor1, task=task_anna_5,
    defaults={'message': 'Задача «Миграция данных из Excel» просрочена!'}
)
Notification.objects.get_or_create(
    user=executor2, task=task_sergey_2,
    defaults={'message': 'Руководитель переоткрыл задачу «Дизайн мобильного приложения».'}
)

# Непрочитанные уведомления для демонстрации счётчика
Notification.objects.get_or_create(
    user=manager, task=task_elena_2,
    defaults={'message': 'Елена Соколова оставила комментарий к задаче «Верстка личного кабинета».',
              'is_read': False}
)
Notification.objects.get_or_create(
    user=manager, task=task_sergey_1,
    defaults={'message': 'Сергей Смирнов оставил комментарий к задаче «Дизайн корпоративного портала».',
              'is_read': False}
)

print('✓ Оповещения созданы')

# ---------------------------------------------------
# 9. KPI
# ---------------------------------------------------

print('Создаю KPI...')

kpi_data = [
    (p1, 'Процент выполнения', 45.00),
    (p1, 'Индекс соблюдения сроков', 85.00),
    (p1, 'Использование ресурсов', 72.50),
    (p2, 'Процент выполнения', 25.00),
    (p2, 'Индекс соблюдения сроков', 78.00),
    (p2, 'Использование ресурсов', 48.00),
    (p3, 'Процент выполнения', 38.00),
    (p3, 'Индекс соблюдения сроков', 90.00),
    (p3, 'Использование ресурсов', 55.00),
    (p4, 'Процент выполнения', 60.00),
    (p4, 'Индекс соблюдения сроков', 70.00),
    (p4, 'Использование ресурсов', 90.00),
    (p5, 'Процент выполнения', 15.00),
    (p5, 'Индекс соблюдения сроков', 40.00),
    (p5, 'Использование ресурсов', 20.00),
]

for project, name, value in kpi_data:
    KPI.objects.get_or_create(project=project, name=name, defaults={'value': value})

print('✓ KPI созданы')

# ---------------------------------------------------
# 10. РИСКИ (для Насти)
# ---------------------------------------------------

print('Создаю риски...')

risk1, _ = Risk.objects.get_or_create(
    title='Уход ключевого разработчика',
    defaults={
        'project': p1, 'task': task_anna_1,
        'description': 'Ведущий разработчик может покинуть проект',
        'probability': prob_medium, 'impact': imp_high,
        'status': risk_analysis, 'responsible': manager,
        'mitigation_plan': 'Подготовить второго сотрудника, документация передана',
        'identified_at': date(2026, 4, 10),
    }
)

risk2, _ = Risk.objects.get_or_create(
    title='Задержка поставки оборудования',
    defaults={
        'project': p1,
        'description': 'Серверное оборудование задержано поставщиком',
        'probability': prob_low, 'impact': imp_medium,
        'status': risk_new, 'responsible': manager,
        'mitigation_plan': 'Поиск альтернативных поставщиков',
        'identified_at': date(2026, 4, 20),
    }
)

# Для Насти: риск со статусом «Приняты меры»
risk3, _ = Risk.objects.get_or_create(
    title='Нарушение сроков тестирования',
    defaults={
        'project': p2,
        'description': 'Команда тестирования не укладывается в график',
        'probability': prob_high, 'impact': imp_medium,
        'status': risk_mitigated, 'responsible': manager,
        'mitigation_plan': 'Привлечён дополнительный тестировщик',
        'identified_at': date(2026, 5, 1),
    }
)

# Для Насти: риск со статусом «Закрыт»
risk4, _ = Risk.objects.get_or_create(
    title='Отказ облачного провайдера',
    defaults={
        'project': p3,
        'description': 'Облачный провайдер может прекратить обслуживание',
        'probability': prob_low, 'impact': imp_critical,
        'status': risk_closed, 'responsible': manager,
        'mitigation_plan': 'Настроено резервное копирование на второй ЦОД',
        'identified_at': date(2026, 5, 5),
    }
)

# Для Насти: критический риск со статусом «Выявлен»
risk5, _ = Risk.objects.get_or_create(
    title='Утечка персональных данных клиентов',
    defaults={
        'project': p1,
        'description': 'Возможна утечка данных из-за уязвимости в модуле авторизации',
        'probability': prob_medium, 'impact': imp_critical,
        'status': risk_new, 'responsible': manager,
        'mitigation_plan': 'Провести аудит безопасности, обновить протоколы шифрования',
        'identified_at': date(2026, 5, 10),
    }
)

print('✓ Риски созданы')

# ---------------------------------------------------
# 11. ИСТОРИЯ ИЗМЕНЕНИЙ РИСКОВ (для Насти)
# ---------------------------------------------------

print('Создаю историю рисков...')

RiskHistory.objects.get_or_create(
    risk=risk1, user=manager,
    defaults={'old_status': risk_new, 'new_status': risk_analysis,
              'comment': 'Начат анализ риска, назначен ответственный', 'changed_at': timezone.now()}
)
RiskHistory.objects.get_or_create(
    risk=risk3, user=manager,
    defaults={'old_status': risk_analysis, 'new_status': risk_mitigated,
              'comment': 'Приняты меры: привлечён дополнительный тестировщик', 'changed_at': timezone.now()}
)
RiskHistory.objects.get_or_create(
    risk=risk4, user=manager,
    defaults={'old_status': risk_mitigated, 'new_status': risk_closed,
              'comment': 'Риск закрыт: настроено резервное копирование', 'changed_at': timezone.now()}
)
RiskHistory.objects.get_or_create(
    risk=risk5, user=manager,
    defaults={'old_status': None, 'new_status': risk_new,
              'comment': 'Риск выявлен в ходе планового аудита', 'changed_at': timezone.now()}
)

print('✓ История рисков создана')

# ---------------------------------------------------
# 12. ОТСУТСТВИЯ СОТРУДНИКОВ
# ---------------------------------------------------

print('Создаю отсутствия...')

UserAbsence.objects.get_or_create(
    user=executor1, start_date=date(2026, 4, 10),
    defaults={'end_date': date(2026, 4, 24), 'absence_type': abs_vacation,
              'reason': 'Ежегодный оплачиваемый отпуск'}
)
UserAbsence.objects.get_or_create(
    user=executor2, start_date=date(2026, 5, 5),
    defaults={'end_date': date(2026, 5, 8), 'absence_type': abs_sick,
              'reason': 'ОРВИ'}
)
# Для Насти: отсутствие типа «Командировка»
UserAbsence.objects.get_or_create(
    user=executor3, start_date=date(2026, 5, 20),
    defaults={'end_date': date(2026, 5, 23), 'absence_type': abs_trip,
              'reason': 'Конференция по мобильной разработке'}
)
# Отсутствие на текущую неделю (для демонстрации загрузки)
UserAbsence.objects.get_or_create(
    user=executor4, start_date=date.today(),
    defaults={'end_date': date.today() + timedelta(days=2),
              'absence_type': abs_dayoff, 'reason': 'Семейные обстоятельства'}
)

print('✓ Отсутствия созданы')

# ---------------------------------------------------
# 13. БЮДЖЕТЫ ПРОЕКТОВ
# ---------------------------------------------------

print('Создаю бюджеты...')

budgets_data = [
    (p1, 1500000, 1200000, date(2026, 4, 1)),
    (p2, 2000000, 600000, date(2026, 4, 25)),
    (p3, 800000, 350000, date(2026, 5, 10)),
    # Для Насти: проект с перерасходом бюджета
    (p4, 900000, 1050000, date(2026, 1, 5)),
    # Для Насти: проект с просроченным сроком
    (p5, 500000, 480000, date(2026, 1, 25)),
]

for project, planned, actual, approved in budgets_data:
    Budget.objects.get_or_create(
        project=project,
        defaults={'planned_amount': planned, 'actual_amount': actual, 'approved_at': approved}
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
print('  marina.vasilyeva  / testpassword123  (руководитель)')
print('  alexey.fedorov    / testpassword123  (руководитель 2)')
print('  anna.petrova      / testpassword123  (исполнитель)')
print('  sergey.smirnov    / testpassword123  (исполнитель)')
print('  dmitry.volkov     / testpassword123  (исполнитель)')
print('  elena.sokolova    / testpassword123  (исполнитель)')
print('  nikolay.ustinov   / testpassword123  (исполнитель без руководителя)')
print('  director          / testpassword123  (директор)')