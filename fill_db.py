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
ts_blocked, _ = TaskStatus.objects.get_or_create(name='Заблокирована', defaults={'order': 6})

manager_group, _ = Group.objects.get_or_create(name='Руководитель проекта')
executor_group, _ = Group.objects.get_or_create(name='Исполнитель')
director_group, _ = Group.objects.get_or_create(name='Директор')

print('✓ Справочники созданы')

# ---------------------------------------------------
# 2. ПОЛЬЗОВАТЕЛИ
# ---------------------------------------------------

print('Создаю пользователей...')

users_data = [
    ('director', 'director@example.com', 'Илья', 'Новиков', [director_group]),
    ('marina.vasilyeva', 'marina@example.com', 'Марина', 'Васильева', [manager_group]),
    ('alexey.fedorov', 'alexey@example.com', 'Алексей', 'Фёдоров', [manager_group]),
    ('anna.petrova', 'anna@example.com', 'Анна', 'Петрова', [executor_group]),
    ('sergey.smirnov', 'sergey@example.com', 'Сергей', 'Смирнов', [executor_group]),
    ('dmitry.volkov', 'dmitry@example.com', 'Дмитрий', 'Волков', [executor_group]),
    ('elena.sokolova', 'elena@example.com', 'Елена', 'Соколова', [executor_group]),
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
        defaults={'manager': manager, 'weekly_work_hours': 40}
    )

# Для Насти: сотрудник без руководителя не создаётся через Employee

print('✓ Связи руководитель-исполнители созданы')

# ---------------------------------------------------
# 4. ПРОЕКТЫ
# ---------------------------------------------------

print('Создаю проекты...')

# ===== ПРОЕКТЫ МАРИНЫ (6 штук, все статусы) =====

p1, _ = Project.objects.get_or_create(
    name='Внедрение CRM-системы',
    defaults={
        'description': 'Автоматизация работы отдела продаж и клиентского сервиса',
        'start_date_plan': date(2026, 3, 1),
        'end_date_plan': date(2026, 7, 30),
        'start_date_fact': date(2026, 3, 5),
        'status': status_active,
        'priority': pr_high,
        'manager': manager,
    }
)

p2, _ = Project.objects.get_or_create(
    name='Мобильное приложение',
    defaults={
        'description': 'Разработка нативного приложения для iOS и Android',
        'start_date_plan': date(2026, 4, 1),
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
        'start_date_plan': date(2026, 4, 15),
        'end_date_plan': date(2026, 8, 30),
        'status': status_active,
        'priority': pr_medium,
        'manager': manager,
    }
)

# Завершённый проект
p4, _ = Project.objects.get_or_create(
    name='Обновление серверной инфраструктуры',
    defaults={
        'description': 'Замена устаревшего серверного оборудования и настройка резервного копирования',
        'start_date_plan': date(2026, 1, 10),
        'end_date_plan': date(2026, 3, 15),
        'start_date_fact': date(2026, 1, 15),
        'end_date_fact': date(2026, 3, 14),
        'status': status_completed,
        'priority': pr_high,
        'manager': manager,
    }
)

# Приостановленный проект
p5, _ = Project.objects.get_or_create(
    name='Система аналитики продаж',
    defaults={
        'description': 'Внедрение BI-инструментов для анализа эффективности продаж',
        'start_date_plan': date(2026, 2, 1),
        'end_date_plan': date(2026, 5, 30),
        'start_date_fact': date(2026, 2, 5),
        'status': status_paused,
        'priority': pr_critical,
        'manager': manager,
    }
)

# Отменённый проект
p6, _ = Project.objects.get_or_create(
    name='Чат-бот для техподдержки',
    defaults={
        'description': 'Разработка чат-бота для автоматизации ответов на типовые обращения клиентов',
        'start_date_plan': date(2026, 5, 1),
        'end_date_plan': date(2026, 6, 15),
        'status': status_cancelled,
        'priority': pr_low,
        'manager': manager,
    }
)

# Пустой проект (для Насти) — оставляем, но без задач
p7, _ = Project.objects.get_or_create(
    name='Портал для партнёров',
    defaults={
        'description': 'Разработка личного кабинета для дилеров и партнёров компании',
        'start_date_plan': date(2026, 7, 1),
        'end_date_plan': date(2026, 10, 1),
        'status': status_active,
        'priority': pr_low,
        'manager': manager,
    }
)

# ===== ПРОЕКТ ВТОРОГО РУКОВОДИТЕЛЯ =====

p8, _ = Project.objects.get_or_create(
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
p4.participants.add(executor1, executor2, executor3)
p5.participants.add(executor1, executor3)
p6.participants.add(executor2, executor4)
p8.participants.add(executor2)

print('✓ Проекты созданы')

# ---------------------------------------------------
# 5. ЗАДАЧИ
# ---------------------------------------------------

print('Создаю задачи...')

now = timezone.now()

# =========================================
# ПРОЕКТ 1: Внедрение CRM-системы (Активен)
# Задач: 8. Готово: 3 → прогресс ~38%
# =========================================

t1_1 = Task.objects.create(title='Разработка модуля контактов', project=p1, description='CRUD-операции для управления контактами клиентов', priority='high', planned_start_date=now - timedelta(days=30), planned_end_date=now - timedelta(days=10), assigned_to=executor1, author=manager, status=ts_done)
t1_2 = Task.objects.create(title='Настройка почтовых уведомлений', project=p1, description='Автоматические письма клиентам при изменении статуса сделки', priority='medium', planned_start_date=now - timedelta(days=28), planned_end_date=now - timedelta(days=14), assigned_to=executor1, author=manager, status=ts_done)
t1_3 = Task.objects.create(title='Миграция данных из Excel', project=p1, description='Перенос клиентской базы из старых таблиц в CRM', priority='high', planned_start_date=now - timedelta(days=20), planned_end_date=now - timedelta(days=5), assigned_to=executor1, author=manager, status=ts_done)
t1_4 = Task.objects.create(title='Интеграция с 1С', project=p1, description='Настройка обмена данными между CRM и учётной системой', priority='critical', planned_start_date=now - timedelta(days=10), planned_end_date=now + timedelta(days=5), assigned_to=executor1, author=manager, status=ts_in_progress)
t1_5 = Task.objects.create(title='Дашборд для руководителя', project=p1, description='Аналитическая панель с графиками по продажам', priority='medium', planned_start_date=now + timedelta(days=3), planned_end_date=now + timedelta(days=20), assigned_to=executor2, author=manager, status=ts_new)
t1_6 = Task.objects.create(title='Обучение сотрудников', project=p1, description='Провести тренинг по работе с новой CRM', priority='medium', planned_start_date=now + timedelta(days=14), planned_end_date=now + timedelta(days=16), assigned_to=executor3, author=manager, status=ts_planned)
t1_7 = Task.objects.create(title='Аудит безопасности CRM', project=p1, description='Проверка уязвимостей и прав доступа', priority='high', planned_start_date=now - timedelta(days=10), planned_end_date=now - timedelta(days=1), assigned_to=executor2, author=manager, status=ts_in_progress)
t1_8 = Task.objects.create(title='Интеграция с телефонией', project=p1, description='Подключение IP-телефонии к CRM', priority='high', planned_start_date=now - timedelta(days=5), planned_end_date=now + timedelta(days=3), assigned_to=executor4, author=manager, status=ts_review)

# =========================================
# ПРОЕКТ 2: Мобильное приложение (Активен)
# Задач: 7. Готово: 2 → прогресс ~29%
# =========================================

t2_1 = Task.objects.create(title='Разработка API', project=p2, description='REST API для мобильного клиента', priority='high', planned_start_date=now - timedelta(days=25), planned_end_date=now - timedelta(days=5), assigned_to=executor3, author=manager, status=ts_done)
t2_2 = Task.objects.create(title='Анимация переходов', project=p2, description='Проработка микроанимаций между экранами приложения', priority='low', planned_start_date=now - timedelta(days=14), planned_end_date=now - timedelta(days=5), assigned_to=executor2, author=manager, status=ts_done)
t2_3 = Task.objects.create(title='Дизайн мобильного приложения', project=p2, description='Макеты экранов для iOS и Android', priority='medium', planned_start_date=now + timedelta(days=5), planned_end_date=now + timedelta(days=25), assigned_to=executor2, author=manager, status=ts_new)
t2_4 = Task.objects.create(title='Иконки приложения', project=p2, description='Разработать набор иконок для всех разделов', priority='medium', planned_start_date=now + timedelta(days=10), planned_end_date=now + timedelta(days=17), assigned_to=executor2, author=manager, status=ts_planned)
t2_5 = Task.objects.create(title='Тестирование API', project=p2, description='Написание и прогон автотестов', priority='medium', planned_start_date=now - timedelta(days=3), planned_end_date=now + timedelta(days=10), assigned_to=executor3, author=manager, status=ts_in_progress)
t2_6 = Task.objects.create(title='Авторизация через соцсети', project=p2, description='Вход через Google и Apple ID', priority='high', planned_start_date=now - timedelta(days=7), planned_end_date=now + timedelta(days=5), assigned_to=executor1, author=manager, status=ts_review)
t2_7 = Task.objects.create(title='Пуш-уведомления', project=p2, description='Настройка Firebase для push-уведомлений', priority='medium', planned_start_date=now - timedelta(days=5), planned_end_date=now - timedelta(days=1), assigned_to=executor1, author=manager, status=ts_in_progress)

# =========================================
# ПРОЕКТ 3: Корпоративный портал (Активен)
# Задач: 8. Готово: 3 → прогресс ~38%
# =========================================

t3_1 = Task.objects.create(title='Дизайн корпоративного портала', project=p3, description='Разработать макеты всех страниц портала', priority='high', planned_start_date=now - timedelta(days=25), planned_end_date=now - timedelta(days=5), assigned_to=executor2, author=manager, status=ts_done)
t3_2 = Task.objects.create(title='Верстка главной страницы', project=p3, description='Адаптивная вёрстка главной страницы портала по макетам', priority='high', planned_start_date=now - timedelta(days=14), planned_end_date=now - timedelta(days=2), assigned_to=executor4, author=manager, status=ts_done)
t3_3 = Task.objects.create(title='Документация для разработчиков', project=p3, description='Описание архитектуры портала и инструкции по развёртыванию', priority='low', planned_start_date=now - timedelta(days=10), planned_end_date=now - timedelta(days=3), assigned_to=executor3, author=manager, status=ts_done)
t3_4 = Task.objects.create(title='Верстка личного кабинета', project=p3, description='Страница профиля сотрудника с настройками', priority='high', planned_start_date=now - timedelta(days=10), planned_end_date=now + timedelta(days=3), assigned_to=executor4, author=manager, status=ts_in_progress)
t3_5 = Task.objects.create(title='Адаптив под мобильные', project=p3, description='Адаптация всех страниц портала под планшеты и смартфоны', priority='medium', planned_start_date=now + timedelta(days=5), planned_end_date=now + timedelta(days=15), assigned_to=executor4, author=manager, status=ts_new)
t3_6 = Task.objects.create(title='Тестирование верстки', project=p3, description='Кроссбраузерное тестирование и исправление багов', priority='low', planned_start_date=now + timedelta(days=16), planned_end_date=now + timedelta(days=20), assigned_to=executor4, author=manager, status=ts_planned)
t3_7 = Task.objects.create(title='Рефакторинг старого кода', project=p3, description='Приведение легаси-модулей портала к общим стандартам', priority='medium', planned_start_date=now - timedelta(days=5), planned_end_date=now + timedelta(days=10), assigned_to=executor3, author=manager, status=ts_in_progress)
t3_8 = Task.objects.create(title='Баннеры для портала', project=p3, description='Разработать рекламные баннеры для главной страницы', priority='low', planned_start_date=now - timedelta(days=3), planned_end_date=now + timedelta(days=5), assigned_to=executor2, author=manager, status=ts_review)

# =========================================
# ПРОЕКТ 4: Обновление серверной инфраструктуры (Завершён)
# Задач: 4. Готово: 4 → прогресс 100%
# =========================================

t4_1 = Task.objects.create(title='Закупка серверного оборудования', project=p4, description='Выбор и закупка новых серверов', priority='high', planned_start_date=now - timedelta(days=60), planned_end_date=now - timedelta(days=45), assigned_to=executor3, author=manager, status=ts_done)
t4_2 = Task.objects.create(title='Настройка резервного копирования', project=p4, description='Настройка автоматического бэкапа на удалённый сервер', priority='critical', planned_start_date=now - timedelta(days=40), planned_end_date=now - timedelta(days=25), assigned_to=executor1, author=manager, status=ts_done)
t4_3 = Task.objects.create(title='Миграция баз данных', project=p4, description='Перенос всех БД на новое оборудование', priority='high', planned_start_date=now - timedelta(days=25), planned_end_date=now - timedelta(days=10), assigned_to=executor2, author=manager, status=ts_done)
t4_4 = Task.objects.create(title='Тестирование отказоустойчивости', project=p4, description='Проверка работы при отключении одного из серверов', priority='medium', planned_start_date=now - timedelta(days=10), planned_end_date=now - timedelta(days=3), assigned_to=executor3, author=manager, status=ts_done)

# =========================================
# ПРОЕКТ 5: Система аналитики продаж (Приостановлен)
# Задач: 5. Готово: 2 → прогресс 40%
# =========================================

t5_1 = Task.objects.create(title='Подключение источников данных', project=p5, description='Интеграция с CRM и 1С для получения данных', priority='high', planned_start_date=now - timedelta(days=40), planned_end_date=now - timedelta(days=25), assigned_to=executor1, author=manager, status=ts_done)
t5_2 = Task.objects.create(title='Разработка модели данных', project=p5, description='Проектирование схемы хранилища данных', priority='high', planned_start_date=now - timedelta(days=30), planned_end_date=now - timedelta(days=18), assigned_to=executor3, author=manager, status=ts_done)
t5_3 = Task.objects.create(title='Настройка BI-дашбордов', project=p5, description='Подключение источников данных и настройка визуализаций', priority='critical', planned_start_date=now - timedelta(days=20), planned_end_date=now - timedelta(days=5), assigned_to=executor1, author=manager, status=ts_in_progress)
t5_4 = Task.objects.create(title='Обучение отдела продаж', project=p5, description='Проведение тренинга по работе с BI-системой', priority='medium', planned_start_date=now + timedelta(days=10), planned_end_date=now + timedelta(days=12), assigned_to=executor3, author=manager, status=ts_planned)
t5_5 = Task.objects.create(title='Аудит качества данных', project=p5, description='Проверка корректности данных из источников', priority='medium', planned_start_date=now - timedelta(days=10), planned_end_date=now - timedelta(days=1), assigned_to=executor1, author=manager, status=ts_review)

# =========================================
# ПРОЕКТ 6: Чат-бот для техподдержки (Отменён)
# Задач: 3. Готово: 1 → прогресс 33%
# =========================================

t6_1 = Task.objects.create(title='Проектирование сценариев диалогов', project=p6, description='Разработка дерева диалогов для типовых обращений', priority='medium', planned_start_date=now - timedelta(days=20), planned_end_date=now - timedelta(days=10), assigned_to=executor2, author=manager, status=ts_done)
t6_2 = Task.objects.create(title='Разработка прототипа бота', project=p6, description='Создание MVP чат-бота на Python', priority='low', planned_start_date=now - timedelta(days=10), planned_end_date=now + timedelta(days=5), assigned_to=executor4, author=manager, status=ts_new)
t6_3 = Task.objects.create(title='Интеграция с Telegram', project=p6, description='Подключение бота к Telegram API', priority='low', planned_start_date=now - timedelta(days=5), planned_end_date=now + timedelta(days=10), assigned_to=executor4, author=manager, status=ts_planned)

# =========================================
# ПРОЕКТ 7: Портал для партнёров (пустой, для Насти)
# =========================================
# Без задач

# =========================================
# ПРОЕКТ 8: Внутренний аудит ИТ-систем (второй руководитель)
# =========================================

t8_1 = Task.objects.create(title='Проверка безопасности серверов', project=p8, description='Аудит конфигурации и прав доступа', priority='high', planned_start_date=now - timedelta(days=5), planned_end_date=now + timedelta(days=10), assigned_to=executor2, author=manager2, status=ts_in_progress)
t8_2 = Task.objects.create(title='Инвентаризация ПО', project=p8, description='Составление реестра установленного программного обеспечения', priority='medium', planned_start_date=now - timedelta(days=10), planned_end_date=now - timedelta(days=3), assigned_to=executor2, author=manager2, status=ts_done)

print('✓ Задачи созданы')

# ---------------------------------------------------
# 6. НАЗНАЧЕНИЯ (плановые и фактические часы)
# ---------------------------------------------------

print('Создаю назначения...')

assignments_data = [
    # Проект 1: CRM
    (t1_1, executor1, 16, 16),
    (t1_2, executor1, 8, 8),
    (t1_3, executor1, 12, 10),
    (t1_4, executor1, 16, 8),
    (t1_5, executor2, 12, 0),
    (t1_6, executor3, 4, 0),
    (t1_7, executor2, 8, 6),
    (t1_8, executor4, 8, 6),

    # Проект 2: Мобильное приложение
    (t2_1, executor3, 16, 16),
    (t2_2, executor2, 8, 8),
    (t2_3, executor2, 16, 0),
    (t2_4, executor2, 6, 0),
    (t2_5, executor3, 12, 6),
    (t2_6, executor1, 8, 4),
    (t2_7, executor1, 8, 6),

    # Проект 3: Корпоративный портал
    (t3_1, executor2, 16, 16),
    (t3_2, executor4, 12, 12),
    (t3_3, executor3, 6, 6),
    (t3_4, executor4, 12, 8),
    (t3_5, executor4, 12, 0),
    (t3_6, executor4, 6, 0),
    (t3_7, executor3, 10, 4),
    (t3_8, executor2, 8, 4),

    # Проект 4: Серверная инфраструктура (все завершены)
    (t4_1, executor3, 16, 16),
    (t4_2, executor1, 12, 12),
    (t4_3, executor2, 16, 16),
    (t4_4, executor3, 8, 8),

    # Проект 5: Аналитика продаж
    (t5_1, executor1, 16, 16),
    (t5_2, executor3, 12, 12),
    (t5_3, executor1, 12, 8),
    (t5_4, executor3, 4, 0),
    (t5_5, executor1, 8, 6),

    # Проект 6: Чат-бот
    (t6_1, executor2, 8, 8),
    (t6_2, executor4, 8, 0),
    (t6_3, executor4, 6, 0),

    # Проект 8: Аудит (второй руководитель)
    (t8_1, executor2, 8, 4),
    (t8_2, executor2, 8, 8),
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
    task=t1_4, author=executor1,
    defaults={'text': 'Интеграция с 1С настроена, проверила на тестовых данных. Жду проверки.'}
)
Comment.objects.get_or_create(
    task=t1_4, author=manager,
    defaults={'text': 'Принято, но нужно добавить обработку ошибок при таймауте.'}
)
Comment.objects.get_or_create(
    task=t3_1, author=executor2,
    defaults={'text': 'Макеты портала готовы, загрузил в Figma. Жду согласования.'}
)
Comment.objects.get_or_create(
    task=t3_2, author=executor4,
    defaults={'text': 'Возникли сложности с сеткой главной страницы, нужно больше времени.'}
)

print('✓ Комментарии созданы')

# ---------------------------------------------------
# 8. ОПОВЕЩЕНИЯ
# ---------------------------------------------------

print('Создаю оповещения...')

Notification.objects.get_or_create(
    user=manager, task=t1_4,
    defaults={'message': 'Анна Петрова перевела задачу «Интеграция с 1С» в статус «На проверке».'}
)
Notification.objects.get_or_create(
    user=executor1, task=t1_4,
    defaults={'message': 'Руководитель оставила комментарий к задаче «Интеграция с 1С».'}
)
Notification.objects.get_or_create(
    user=manager, task=t3_4,
    defaults={'message': 'Елена Соколова перевела задачу «Верстка личного кабинета» в статус «На проверке».'}
)
Notification.objects.get_or_create(
    user=executor1, task=t1_7,
    defaults={'message': 'Задача «Аудит безопасности CRM» просрочена!'}
)
Notification.objects.get_or_create(
    user=executor2, task=t2_3,
    defaults={'message': 'Руководитель переоткрыл задачу «Дизайн мобильного приложения».'}
)

# Непрочитанные уведомления для демонстрации счётчика
Notification.objects.get_or_create(
    user=manager, task=t3_4,
    defaults={'message': 'Елена Соколова оставила комментарий к задаче «Верстка личного кабинета».',
              'is_read': False}
)
Notification.objects.get_or_create(
    user=manager, task=t3_1,
    defaults={'message': 'Сергей Смирнов оставил комментарий к задаче «Дизайн корпоративного портала».',
              'is_read': False}
)

print('✓ Оповещения созданы')

# ---------------------------------------------------
# 9. KPI — теперь рассчитываются автоматически в dashboard и project_detail
# ---------------------------------------------------

print('Пропускаю создание KPI — они рассчитываются автоматически')

# ---------------------------------------------------
# 10. РИСКИ (для Насти)
# ---------------------------------------------------

print('Создаю риски...')

risk1, _ = Risk.objects.get_or_create(
    title='Уход ключевого разработчика',
    defaults={
        'project': p1, 'task': t1_1,
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
UserAbsence.objects.get_or_create(
    user=executor3, start_date=date(2026, 5, 20),
    defaults={'end_date': date(2026, 5, 23), 'absence_type': abs_trip,
              'reason': 'Конференция по мобильной разработке'}
)
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
    (p4, 900000, 1050000, date(2026, 1, 5)),
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