from django import forms
from django.contrib.auth import get_user_model
from .models import GphDocument
from ncasign.models import User
from django.utils import timezone

User = get_user_model()

class GPHContractForm(forms.Form):
    """Форма для создания ГПХ договора"""
    
    executor = forms.ModelChoiceField(
        queryset=User.objects.filter(role=4).order_by('full_name'),
        empty_label="Выберите исполнителя",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Исполнитель',
        required=True
    )
    
    approvers = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=3).order_by('full_name'),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'id': 'id_approvers', 'style': 'display:none;'}),
        label='Согласующие',
        required=False
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Дата начала оказания услуг'
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Дата окончания оказания услуг'
    )

class ActForm(forms.Form):
    """Форма для создания акта"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Получаем пользователей с их данными
        User = get_user_model()
        users = User.objects.filter(role=4).order_by('full_name')
        
        # Создаем опции с данными пользователей
        choices = [('', 'Выберите исполнителя')]
        for user in users:
            choices.append((user.username, f'{user.full_name} ({user.username})'))
        
        self.fields['executor'].choices = choices
    
    executor = forms.ChoiceField(
        label='Исполнитель',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'executor-select'})
    )
    full_name = forms.CharField(
        label='ФИО исполнителя',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'full-name-input'})
    )
    phone_number = forms.CharField(
        label='Номер телефона',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'phone-input'})
    )
    iin = forms.CharField(
        label='ИИН',
        max_length=12,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'iin-input'})
    )

    start_date = forms.DateField(
        label='Дата начала работ',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'start-date-input'})
    )
    end_date = forms.DateField(
        label='Дата окончания работ',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'end-date-input'})
    )
    quantity = forms.CharField(
        label='Количество',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'quantity-input'})
    )
    unit_price = forms.CharField(
        label='Цена за единицу',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'unit-price-input'})
    )
    amount = forms.CharField(
        label='Стоимость',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'amount-input', 'readonly': 'readonly'})
    )
    
    approvers = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=3).order_by('full_name'),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'id': 'id_approvers', 'style': 'display:none;'}),
        label='Согласующие',
        required=False
    ) 