from django import forms
from .models import Project, Priority, ProjectStatus, Employee
from task_management.models import Task, TaskStatus
from django.contrib.auth.models import User

class ProjectForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Участники проекта'
    )

    class Meta:
        model = Project
        fields = [
            'name', 'description',
            'start_date_plan', 'end_date_plan',
            'start_date_fact', 'end_date_fact',
            'status', 'priority', 'participants',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Название проекта'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Цели, задачи, ожидаемые результаты'}),
            'start_date_plan': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'end_date_plan': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'start_date_fact': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'end_date_fact': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'name': 'Название проекта',
            'description': 'Описание',
            'start_date_plan': 'Плановая дата начала',
            'end_date_plan': 'Плановая дата окончания',
            'start_date_fact': 'Фактическая дата начала',
            'end_date_fact': 'Фактическая дата окончания',
            'priority': 'Приоритет',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            employee_ids = Employee.objects.filter(manager=user).values_list('employee_id', flat=True)
            self.fields['participants'].queryset = User.objects.filter(id__in=employee_ids)
            self.fields['participants'].label_from_instance = lambda obj: obj.get_full_name() or obj.username

class TaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'planned_end_date', 'assigned_to']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Название задачи'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': 'Описание задачи'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'planned_end_date': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'title': 'Название задачи',
            'description': 'Описание',
            'priority': 'Приоритет',
            'planned_end_date': 'Срок выполнения',
            'assigned_to': 'Исполнитель',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)
        self.fields['assigned_to'].required = False