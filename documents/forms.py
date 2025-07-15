from django import forms
from django.contrib.auth import get_user_model

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