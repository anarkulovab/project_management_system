from django import forms
from .models import Project, Priority, ProjectStatus
from task_management.models import Task, TaskStatus
from django.contrib.auth.models import User

class ProjectForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True, is_superuser=False),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Участники проекта'
    )

    class Meta:
        model = Project
        fields = [
            'name',
            'description',
            'start_date_plan',
            'end_date_plan',
            'priority',
            'participants',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Название проекта'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Цели, задачи, ожидаемые результаты'
            }),
            'start_date_plan': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'end_date_plan': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'name': 'Название проекта',
            'description': 'Описание',
            'start_date_plan': 'Плановая дата начала',
            'end_date_plan': 'Плановая дата окончания',
            'priority': 'Приоритет',
        }

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