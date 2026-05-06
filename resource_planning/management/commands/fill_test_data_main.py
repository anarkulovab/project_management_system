from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from resource_planning.models import (
    ProjectStatus, Priority, AbsenceType,
    ProbabilityLevel, ImpactLevel, RiskStatus,
    Project, TaskAssignment, UserAbsence,
    Risk, RiskHistory, Budget, KPI, Employee
)
from task_management.models import Task, TaskStatus


class Command(BaseCommand):
    help = 'Заполняет базу данных тестовыми данными'

    def handle(self, *args, **kwargs):
        # ---------------------------------------------------
        # 1. СПРАВОЧНИКИ
        # ---------------------------------------------------

        # Статусы проектов
        status_active, _ = ProjectStatus.objects.get_or_create(name='Активен')
        status_paused, _ = ProjectStatus.objects.get_or_create(name='Приостановлен')
        status_completed, _ = ProjectStatus.objects.get_or_create(name='Завершён')
        status_cancelled, _ = ProjectStatus.objects.get_or_create(name='Отменён')
        self.stdout.write(self.style.SUCCESS('✓ Статусы проектов созданы'))

        # Приоритеты
        pr_low, _ = Priority.objects.get_or_create(name='Низкий')
        pr_medium, _ = Priority.objects.get_or_create(name='Средний')
        pr_high, _ = Priority.objects.get_or_create(name='Высокий')
        pr_critical, _ = Priority.objects.get_or_create(name='Критический')
        self.stdout.write(self.style.SUCCESS('✓ Приоритеты созданы'))

        # Типы отсутствий
        abs_vacation, _ = AbsenceType.objects.get_or_create(name='Отпуск')
        abs_sick, _ = AbsenceType.objects.get_or_create(name='Больничный')
        abs_dayoff, _ = AbsenceType.objects.get_or_create(name='Отгул')
        abs_trip, _ = AbsenceType.objects.get_or_create(name='Командировка')
        self.stdout.write(self.style.SUCCESS('✓ Типы отсутствий созданы'))

        # Уровни вероятности рисков
        prob_low, _ = ProbabilityLevel.objects.get_or_create(name='Низкая')
        prob_medium, _ = ProbabilityLevel.objects.get_or_create(name='Средняя')
        prob_high, _ = ProbabilityLevel.objects.get_or_create(name='Высокая')
        self.stdout.write(self.style.SUCCESS('✓ Уровни вероятности созданы'))

        # Уровни влияния рисков
        imp_low, _ = ImpactLevel.objects.get_or_create(name='Низкое')
        imp_medium, _ = ImpactLevel.objects.get_or_create(name='Среднее')
        imp_high, _ = ImpactLevel.objects.get_or_create(name='Высокое')
        imp_critical, _ = ImpactLevel.objects.get_or_create(name='Критическое')
        self.stdout.write(self.style.SUCCESS('✓ Уровни влияния созданы'))

        # Статусы рисков
        risk_new, _ = RiskStatus.objects.get_or_create(name='Выявлен')
        risk_analysis, _ = RiskStatus.objects.get_or_create(name='Анализируется')
        risk_mitigated, _ = RiskStatus.objects.get_or_create(name='Приняты меры')
        risk_closed, _ = RiskStatus.objects.get_or_create(name='Закрыт')
        self.stdout.write(self.style.SUCCESS('✓ Статусы рисков созданы'))

        # Статусы задач
        ts_new, _ = TaskStatus.objects.get_or_create(name='Новая', defaults={'order': 1})
        ts_in_progress, _ = TaskStatus.objects.get_or_create(name='В работе', defaults={'order': 2})
        ts_review, _ = TaskStatus.objects.get_or_create(name='На проверке', defaults={'order': 3})
        ts_done, _ = TaskStatus.objects.get_or_create(name='Готово', defaults={'order': 4})
        ts_blocked, _ = TaskStatus.objects.get_or_create(name='Заблокирована', defaults={'order': 5})
        self.stdout.write(self.style.SUCCESS('✓ Статусы задач созданы'))

        # ---------------------------------------------------
        # 2. ПОЛЬЗОВАТЕЛИ
        # ---------------------------------------------------

        users = [
            ('director', 'director@example.com', 'Иван', 'Директоров'),
            ('manager', 'manager@example.com', 'Пётр', 'Руководителев'),
            ('executor1', 'executor1@example.com', 'Анна', 'Исполнителева'),
            ('executor2', 'executor2@example.com', 'Сергей', 'Исполнителев'),
        ]
        created_users = {}
        for username, email, first_name, last_name in users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'first_name': first_name, 'last_name': last_name}
            )
            if created:
                user.set_password('testpassword123')
                user.save()
            created_users[username] = user

        director = created_users['director']
        manager = created_users['manager']
        executor1 = created_users['executor1']
        executor2 = created_users['executor2']
        self.stdout.write(self.style.SUCCESS('✓ Пользователи созданы'))

        # ---------------------------------------------------
        # 3. ПРОЕКТЫ
        # ---------------------------------------------------

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

        p4, _ = Project.objects.get_or_create(
            name='Обновление корпоративного портала',
            defaults={
                'description': 'Редизайн и оптимизация внутреннего портала компании',
                'start_date_plan': date(2026, 4, 1),
                'end_date_plan': date(2026, 7, 15),
                'status': status_active,
                'priority': pr_low,
                'manager': manager,
            }
        )

        p5, _ = Project.objects.get_or_create(
            name='Система аналитики продаж',
            defaults={
                'description': 'Внедрение BI-инструментов для отдела продаж',
                'start_date_plan': date(2026, 5, 1),
                'end_date_plan': date(2026, 9, 30),
                'status': status_paused,
                'priority': pr_medium,
                'manager': manager,
            }
        )
        self.stdout.write(self.style.SUCCESS('✓ Проекты созданы'))

        # ---------------------------------------------------
        # 4. ЗАДАЧИ (для модуля Вики)
        # ---------------------------------------------------

        t1_1, _ = Task.objects.get_or_create(
            title='Разработка архитектуры CRM',
            defaults={
                'project': p1,
                'description': 'Спроектировать модульную архитектуру системы',
                'priority': 'high',
                'planned_end_date': timezone.now() + timedelta(days=30),
                'assigned_to': executor1,
                'author': manager,
                'status': ts_done,
            }
        )

        t1_2, _ = Task.objects.get_or_create(
            title='Создание интерфейса CRM',
            defaults={
                'project': p1,
                'description': 'Разработать UI для менеджеров по продажам',
                'priority': 'high',
                'planned_end_date': timezone.now() + timedelta(days=45),
                'assigned_to': executor2,
                'author': manager,
                'status': ts_in_progress,
            }
        )

        t1_3, _ = Task.objects.get_or_create(
            title='Тестирование CRM',
            defaults={
                'project': p1,
                'description': 'Провести функциональное и нагрузочное тестирование',
                'priority': 'medium',
                'planned_end_date': timezone.now() + timedelta(days=60),
                'assigned_to': executor1,
                'author': manager,
                'status': ts_new,
            }
        )

        t2_1, _ = Task.objects.get_or_create(
            title='Настройка ERP-модуля',
            defaults={
                'project': p2,
                'description': 'Адаптировать ERP под бизнес-процессы компании',
                'priority': 'critical',
                'planned_end_date': timezone.now() - timedelta(days=30),
                'assigned_to': executor1,
                'author': manager,
                'status': ts_done,
            }
        )

        t3_1, _ = Task.objects.get_or_create(
            title='Дизайн мобильного приложения',
            defaults={
                'project': p3,
                'description': 'Разработать макеты всех экранов приложения',
                'priority': 'medium',
                'planned_end_date': timezone.now() + timedelta(days=20),
                'assigned_to': executor2,
                'author': manager,
                'status': ts_in_progress,
            }
        )

        t3_2, _ = Task.objects.get_or_create(
            title='Разработка API для приложения',
            defaults={
                'project': p3,
                'description': 'Создать REST API для мобильного клиента',
                'priority': 'high',
                'planned_end_date': timezone.now() + timedelta(days=50),
                'assigned_to': executor1,
                'author': manager,
                'status': ts_new,
            }
        )
        self.stdout.write(self.style.SUCCESS('✓ Задачи созданы'))

        # ---------------------------------------------------
        # 5. НАЗНАЧЕНИЯ НА ЗАДАЧИ
        # ---------------------------------------------------

        assignments_data = [
            (t1_1, executor1, 40, 38),
            (t1_2, executor2, 60, 25),
            (t1_3, executor1, 80, 0),
            (t2_1, executor1, 120, 115),
            (t3_1, executor2, 40, 10),
            (t3_2, executor1, 100, 0),
        ]

        for task, user, planned, actual in assignments_data:
            TaskAssignment.objects.get_or_create(
                task=task,
                user=user,
                defaults={
                    'planned_hours': planned,
                    'actual_hours': actual,
                    'assigned_at': timezone.now(),
                }
            )
        self.stdout.write(self.style.SUCCESS('✓ Назначения созданы'))

        # ---------------------------------------------------
        # 6. КОММЕНТАРИИ (для модуля Вики)
        # ---------------------------------------------------
        # Комментарии создаются в отдельном скрипте Вики

        # ---------------------------------------------------
        # 7. БЮДЖЕТЫ ПРОЕКТОВ
        # ---------------------------------------------------

        budgets_data = [
            (p1, 1500000, 1200000, date(2026, 1, 10)),
            (p2, 800000, 800000, date(2026, 1, 25)),
            (p3, 2000000, 600000, date(2026, 2, 15)),
            (p4, 500000, 150000, date(2026, 3, 20)),
            (p5, 1200000, 0, None),
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
        self.stdout.write(self.style.SUCCESS('✓ Бюджеты созданы'))

        # ---------------------------------------------------
        # 8. РИСКИ
        # ---------------------------------------------------

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

        risk5, _ = Risk.objects.get_or_create(
            title='Изменение требований заказчиком',
            defaults={
                'project': p4,
                'description': 'Заказчик может изменить требования в процессе разработки',
                'probability': prob_medium,
                'impact': imp_medium,
                'status': risk_new,
                'responsible': manager,
                'mitigation_plan': 'Закрепить требования в договоре, согласовывать изменения',
                'identified_at': date(2026, 4, 10),
            }
        )

        risk6, _ = Risk.objects.get_or_create(
            title='Риск завершённого проекта',
            defaults={
                'project': p2,
                'description': 'Тестовый риск для закрытого проекта',
                'probability': prob_low,
                'impact': imp_low,
                'status': risk_closed,
                'responsible': manager,
                'mitigation_plan': 'Риск был успешно обработан',
                'identified_at': date(2026, 2, 15),
            }
        )
        self.stdout.write(self.style.SUCCESS('✓ Риски созданы'))

        # ---------------------------------------------------
        # 9. ИСТОРИЯ ИЗМЕНЕНИЙ РИСКОВ
        # ---------------------------------------------------

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

        RiskHistory.objects.get_or_create(
            risk=risk6,
            defaults={
                'user': manager,
                'old_status': risk_mitigated,
                'new_status': risk_closed,
                'comment': 'Риск успешно обработан, проект завершён',
                'changed_at': timezone.now(),
            }
        )
        self.stdout.write(self.style.SUCCESS('✓ История рисков создана'))

        # ---------------------------------------------------
        # 10. ОТСУТСТВИЯ СОТРУДНИКОВ
        # ---------------------------------------------------

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

        UserAbsence.objects.get_or_create(
            user=manager,
            start_date=date(2026, 6, 1),
            defaults={
                'end_date': date(2026, 6, 5),
                'absence_type': abs_trip,
                'reason': 'Конференция по управлению проектами',
            }
        )
        self.stdout.write(self.style.SUCCESS('✓ Отсутствия созданы'))

        # ---------------------------------------------------
        # 11. KPI ПОКАЗАТЕЛИ
        # ---------------------------------------------------

        # KPI для проекта CRM
        KPI.objects.get_or_create(
            project=p1,
            name='Процент выполнения',
            defaults={'value': 45.00}
        )
        KPI.objects.get_or_create(
            project=p1,
            name='Индекс соблюдения сроков',
            defaults={'value': 0.85}
        )
        KPI.objects.get_or_create(
            project=p1,
            name='Утилизация ресурсов',
            defaults={'value': 72.50}
        )
        KPI.objects.get_or_create(
            project=p1,
            name='Доля просроченных задач',
            defaults={'value': 10.00}
        )

        # KPI для проекта ERP (завершён)
        KPI.objects.get_or_create(
            project=p2,
            name='Процент выполнения',
            defaults={'value': 100.00}
        )
        KPI.objects.get_or_create(
            project=p2,
            name='Индекс соблюдения сроков',
            defaults={'value': 0.95}
        )
        KPI.objects.get_or_create(
            project=p2,
            name='Утилизация ресурсов',
            defaults={'value': 88.00}
        )
        KPI.objects.get_or_create(
            project=p2,
            name='Доля просроченных задач',
            defaults={'value': 0.00}
        )

        # KPI для мобильного приложения
        KPI.objects.get_or_create(
            project=p3,
            name='Процент выполнения',
            defaults={'value': 20.00}
        )
        KPI.objects.get_or_create(
            project=p3,
            name='Индекс соблюдения сроков',
            defaults={'value': 0.70}
        )
        KPI.objects.get_or_create(
            project=p3,
            name='Утилизация ресурсов',
            defaults={'value': 55.00}
        )
        KPI.objects.get_or_create(
            project=p3,
            name='Доля просроченных задач',
            defaults={'value': 15.00}
        )

        # KPI для портала
        KPI.objects.get_or_create(
            project=p4,
            name='Процент выполнения',
            defaults={'value': 35.00}
        )
        KPI.objects.get_or_create(
            project=p4,
            name='Индекс соблюдения сроков',
            defaults={'value': 0.90}
        )

        # KPI для аналитики (приостановлен)
        KPI.objects.get_or_create(
            project=p5,
            name='Процент выполнения',
            defaults={'value': 10.00}
        )
        KPI.objects.get_or_create(
            project=p5,
            name='Индекс соблюдения сроков',
            defaults={'value': 0.60}
        )
        self.stdout.write(self.style.SUCCESS('✓ KPI показатели созданы'))

        # ---------------------------------------------------
        # ИТОГО
        # ---------------------------------------------------
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('ВСЕ ТЕСТОВЫЕ ДАННЫЕ УСПЕШНО ЗАГРУЖЕНЫ'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # ---------------------------------------------------
        # 12. СВЯЗЬ РУКОВОДИТЕЛЬ — ИСПОЛНИТЕЛИ (Employee)
        # ---------------------------------------------------
        manager = User.objects.get(username='manager')
        executor1 = User.objects.get(username='executor1')
        executor2 = User.objects.get(username='executor2')

        Employee.objects.get_or_create(manager=manager, employee=executor1)
        Employee.objects.get_or_create(manager=manager, employee=executor2)

        self.stdout.write(self.style.SUCCESS('✓ Связи руководитель-исполнители созданы'))