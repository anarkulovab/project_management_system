from django.http import JsonResponse
from django.views import View
from resource_planning.models import Project, Budget, Risk, RiskHistory, KPI, ProbabilityLevel, ImpactLevel, RiskStatus
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from task_management.models import Task
from django.contrib.auth.models import User
from task_management.models import Task
from django.contrib.auth.models import User
from resource_planning.models import Employee
import json
from django.contrib.auth import authenticate
@method_decorator(csrf_exempt, name='dispatch')
class ProjectListView(View):
    def get(self, request):
        projects = Project.objects.select_related('status', 'priority', 'manager').all()
        data = []
        for p in projects:
            data.append({
                "project_id": p.id,
                "project_name": p.name,
                "description": p.description,
                "status": p.status.name if p.status else None,
                "priority": p.priority.name if p.priority else None,
                "manager": p.manager.get_full_name() if p.manager else None,
                "start_date_plan": str(p.start_date_plan) if p.start_date_plan else None,
                "end_date_plan": str(p.end_date_plan) if p.end_date_plan else None,
            })
        return JsonResponse(data, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class ProjectDetailView(View):
    def get(self, request, project_id):
        try:
            p = Project.objects.select_related('status', 'priority', 'manager').get(pk=project_id)
        except Project.DoesNotExist:
            return JsonResponse({"error": "Проект не найден"}, status=404)

        budgets = list(Budget.objects.filter(project=p).values(
            'id', 'planned_amount', 'actual_amount', 'approved_at', 'notes'
        ))
        risks = list(Risk.objects.filter(project=p).select_related(
            'probability', 'impact', 'status', 'responsible'
        ).values(
            'id', 'title', 'description',
            'probability__name', 'impact__name',
            'status__name', 'responsible__first_name', 'responsible__last_name',
            'mitigation_plan', 'identified_at'
        ))

        return JsonResponse({
            "project": {
                "project_id": p.id,
                "project_name": p.name,
                "description": p.description,
                "status": p.status.name if p.status else None,
                "priority": p.priority.name if p.priority else None,
                "manager": p.manager.get_full_name() if p.manager else None,
                "start_date_plan": str(p.start_date_plan) if p.start_date_plan else None,
                "end_date_plan": str(p.end_date_plan) if p.end_date_plan else None,
                "start_date_fact": str(p.start_date_fact) if p.start_date_fact else None,
                "end_date_fact": str(p.end_date_fact) if p.end_date_fact else None,
            },
            "budgets": budgets,
            "risks": risks,
        })


@method_decorator(csrf_exempt, name='dispatch')
class BudgetListView(View):
    def get(self, request):
        project_id = request.GET.get('project_id')
        budgets = Budget.objects.filter(project_id=project_id) if project_id else Budget.objects.all()
        return JsonResponse(list(budgets.values()), safe=False)

    def post(self, request):
        import json
        data = json.loads(request.body)
        project_id = data.get('project_id')
        # Проверяем, существует ли уже бюджет для этого проекта (OneToOne)
        budget, created = Budget.objects.update_or_create(
            project_id=project_id,
            defaults={
                'planned_amount': data.get('planned_amount', 0),
                'actual_amount': data.get('actual_amount', 0),
                'approved_at': data.get('approved_at'),
            }
        )
        return JsonResponse({"budget_id": budget.pk, "status": "updated" if not created else "created"},
                            status=200 if not created else 201)


@method_decorator(csrf_exempt, name='dispatch')
class RiskListView(View):
    def get(self, request):
        risks = Risk.objects.select_related('project', 'probability', 'impact', 'status', 'responsible').all()
        data = []
        for r in risks:
            data.append({
                "risk_id": r.id,
                "project_id": r.project_id,
                "project_name": r.project.name if r.project else '',
                "title": r.title,
                "description": r.description,
                "probability": r.probability.name if r.probability else None,
                "impact": r.impact.name if r.impact else None,
                "status": r.status.name if r.status else None,
                "responsible": r.responsible.get_full_name() if r.responsible else None,
                "mitigation_plan": r.mitigation_plan,
                "identified_at": str(r.identified_at),
            })
        return JsonResponse(data, safe=False)

    def post(self, request):
        import json
        data = json.loads(request.body)
        risk = Risk.objects.create(
            project_id=data.get('project_id'),
            title=data.get('title'),
            description=data.get('description', ''),
            probability=ProbabilityLevel.objects.first(),
            impact=ImpactLevel.objects.first(),
            status=RiskStatus.objects.first(),
        )
        return JsonResponse({"risk_id": risk.pk, "status": "created"}, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class RiskUpdateView(View):
    def put(self, request, risk_id):
        import json
        data = json.loads(request.body)
        try:
            risk = Risk.objects.get(pk=risk_id)
            risk.title = data.get('title', risk.title)
            risk.description = data.get('description', risk.description)
            if data.get('status'):
                status = RiskStatus.objects.get(name=data['status'])
                risk.status = status
            risk.save()
            return JsonResponse({"risk_id": risk.pk, "status": "updated"})
        except Risk.DoesNotExist:
            return JsonResponse({"error": "Риск не найден"}, status=404)
@method_decorator(csrf_exempt, name='dispatch')
class RiskHistoryView(View):
    """GET /api/risks/<id>/history/ — история изменений риска."""
    def get(self, request, risk_id):
        try:
            risk = Risk.objects.get(pk=risk_id)
            history = RiskHistory.objects.filter(risk=risk).select_related('user', 'old_status', 'new_status').order_by('-changed_at')
            data = []
            for h in history:
                data.append({
                    "id": h.id,
                    "user": h.user.get_full_name() if h.user else "Система",
                    "old_status": h.old_status.name if h.old_status else "Создание",
                    "new_status": h.new_status.name if h.new_status else "—",
                    "comment": h.comment or "",
                    "changed_at": h.changed_at.strftime("%d.%m.%Y %H:%M"),
                })
            return JsonResponse(data, safe=False)
        except Risk.DoesNotExist:
            return JsonResponse({"error": "Риск не найден"}, status=404)
@method_decorator(csrf_exempt, name='dispatch')
class TeamView(View):
    """GET /api/team/ — расширенная сводка по команде."""
    def get(self, request):
        users = User.objects.all()
        projects = Project.objects.select_related('manager').all()
        risks = Risk.objects.select_related('responsible').all()

        team = {}
        for u in users:
            user_id = u.id
            team[user_id] = {
                "id": user_id,
                "name": u.get_full_name() or u.username,
                "email": u.email or "",
                "role": "Исполнитель",
                "projects_managed": 0,
                "tasks_count": 0,
                "risks_count": 0,
                "last_login": u.last_login.strftime("%d.%m.%Y") if u.last_login else "Никогда",
            }

        for p in projects:
            if p.manager and p.manager.id in team:
                team[p.manager.id]["role"] = "Руководитель"
                team[p.manager.id]["projects_managed"] += 1

        for r in risks:
            if r.responsible and r.responsible.id in team:
                team[r.responsible.id]["risks_count"] += 1

        # Считаем задачи по исполнителям
        try:
            from task_management.models import Task
            tasks = Task.objects.select_related('assigned_to').all()
            for t in tasks:
                if t.assigned_to and t.assigned_to.id in team:
                    team[t.assigned_to.id]["tasks_count"] += 1
        except Exception as e:
            print(f"Ошибка при подсчёте задач: {e}")
        # Отладка
        for uid, data in team.items():
            if data['tasks_count'] > 0:
                print(f"  {data['name']}: {data['tasks_count']} задач")

        return JsonResponse(list(team.values()), safe=False)
@method_decorator(csrf_exempt, name='dispatch')
class AuditLogView(View):
    """GET /api/audit/ — журнал действий в системе."""
    def get(self, request):
        logs = []
        # История изменений рисков
        risk_history = RiskHistory.objects.select_related('user', 'risk', 'old_status', 'new_status').order_by('-changed_at')[:20]
        for h in risk_history:
            logs.append({
                "action": "Изменение статуса риска",
                "detail": f"Риск «{h.risk.title}» → {h.new_status.name if h.new_status else '—'}",
                "user": h.user.get_full_name() if h.user else "Система",
                "timestamp": h.changed_at.strftime("%d.%m.%Y %H:%M"),
            })
        # Создание бюджетов
        budgets = Budget.objects.select_related('project').order_by('-approved_at')[:10]
        for b in budgets:
            if b.approved_at:
                logs.append({
                    "action": "Утверждение бюджета",
                    "detail": f"Проект «{b.project.name}»: {b.planned_amount:,.0f} ₽",
                    "user": "Директор",
                    "timestamp": b.approved_at.strftime("%d.%m.%Y"),
                })
        # Создание проектов
        projects = Project.objects.select_related('manager').order_by('-created_at')[:10]
        for p in projects:
            logs.append({
                "action": "Создание проекта",
                "detail": f"Проект «{p.name}»",
                "user": p.manager.get_full_name() if p.manager else "Система",
                "timestamp": p.created_at.strftime("%d.%m.%Y"),
            })
        # Сортируем по дате
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        return JsonResponse(logs[:30], safe=False)
@method_decorator(csrf_exempt, name='dispatch')
class UserDeleteView(View):
    """DELETE /api/users/<id>/ — удаление пользователя (только для директора)."""
    def delete(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
            username = user.username
            user.delete()
            return JsonResponse({"status": "deleted", "username": username})
        except User.DoesNotExist:
            return JsonResponse({"error": "Пользователь не найден"}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class UserTransferView(View):
    """PUT /api/users/<id>/transfer/ — перевод сотрудника к другому руководителю."""
    def put(self, request, user_id):
        try:
            data = json.loads(request.body)
            new_manager_id = data.get('new_manager_id')
            if not new_manager_id:
                return JsonResponse({"error": "new_manager_id обязателен"}, status=400)

            user = User.objects.get(pk=user_id)
            new_manager = User.objects.get(pk=new_manager_id)

            # Обновляем или создаём запись в Employee
            employee_rel, created = Employee.objects.update_or_create(
                employee=user,
                defaults={'manager': new_manager}
            )

            return JsonResponse({
                "status": "transferred",
                "user": user.get_full_name() or user.username,
                "new_manager": new_manager.get_full_name() or new_manager.username
            })
        except User.DoesNotExist:
            return JsonResponse({"error": "Пользователь не найден"}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Некорректный JSON"}, status=400)
class KPIListView(View):
    """GET /api/kpi/ — показатели KPI по проектам."""
    def get(self, request):
        project_id = request.GET.get('project_id')
        kpis = KPI.objects.filter(project_id=project_id) if project_id else KPI.objects.all()
        return JsonResponse(list(kpis.values()), safe=False)
class ProjectTasksView(View):
    """GET /api/projects/<id>/tasks/ — список задач проекта."""
    def get(self, request, project_id):
        try:
            project = Project.objects.get(pk=project_id)
            tasks = Task.objects.filter(project=project).select_related('status', 'assigned_to').order_by('planned_end_date')
            data = []
            for t in tasks:
                data.append({
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.name if t.status else "—",
                    "assignee": t.assigned_to.get_full_name() if t.assigned_to else "—",
                    "planned_start": t.planned_start_date.strftime("%Y-%m-%d") if t.planned_start_date else None,
                    "planned_end": t.planned_end_date.strftime("%Y-%m-%d") if t.planned_end_date else None,
                    "priority": t.priority,
                })
            return JsonResponse(data, safe=False)
        except Project.DoesNotExist:
            return JsonResponse({"error": "Проект не найден"}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class DesktopLoginView(View):
    """
    POST /api/desktop-login/
    Вход для десктоп-клиента.
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Неверный формат данных'}, status=400)

        username = data.get('username', '')
        password = data.get('password', '')

        if not username or not password:
            return JsonResponse({'success': False, 'error': 'Введите логин и пароль'}, status=400)

        user = authenticate(username=username, password=password)

        if user is None:
            return JsonResponse({'success': False, 'error': 'Неверный логин или пароль'}, status=401)

        if not user.is_active:
            return JsonResponse({'success': False, 'error': 'Учётная запись отключена'}, status=403)

        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'name': f'{user.first_name} {user.last_name}'.strip() or user.username,
                'email': user.email or '',
            }
        })