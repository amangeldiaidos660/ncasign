from django import forms
from django.contrib.auth.forms import AuthenticationForm
from ncasign.models import User
from datetime import datetime
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ID или Email',
            'type': 'text',
            'autocomplete': 'username',
            'spellcheck': 'false'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль',
            'autocomplete': 'current-password'
        })
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        if username:
            if '@' in username:
                try:
                    user = User.objects.get(email=username)
                    return user.username
                except User.DoesNotExist:
                    raise forms.ValidationError('Пользователь с таким email не найден')
            else:
                return username
        
        return username

class CustomUserCreationForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ФИО'
        })
    )
    position = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Должность'
        }),
        label='Должность',
        required=False
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    iin = forms.CharField(
        max_length=12,
        min_length=12,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ИИН (12 цифр)'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Телефон'
        })
    )
    proxy_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Номер доверенности'
        }),
        label='Номер доверенности',
        required=False
    )
    proxy_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'Дата доверенности',
            'id': 'proxy_date'
        }, format='%Y-%m-%d'),
        label='Дата доверенности',
        required=False
    )

    class Meta:
        model = User
        fields = ('full_name', 'position', 'email', 'role', 'iin', 'phone_number', 'proxy_number', 'proxy_date')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proxy_number'].required = False
        self.fields['proxy_date'].required = False
    
    def save(self, commit=True):
        user = super().save(commit=False)
        current_year = str(datetime.now().year)[2:]  
        last_user = User.objects.filter(username__startswith=current_year).order_by('-username').first()
        
        if last_user:
            try:
                last_number = int(last_user.username[2:])
                new_number = last_number + 1
            except ValueError:
                new_number = 1
        else:
            new_number = 1
        
        user.username = f"{current_year}{new_number:04d}"
        user.set_password('Qwerty#01')
        
        if commit:
            user.save()
        return user


class UserEditForm(UserChangeForm):
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ФИО'
        })
    )
    position = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Должность'
        }),
        label='Должность',
        required=False
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    iin = forms.CharField(
        max_length=12,
        min_length=12,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ИИН (12 цифр)'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Телефон'
        })
    )
    proxy_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Номер доверенности'
        }),
        label='Номер доверенности',
        required=False
    )
    proxy_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'Дата доверенности',
            'id': 'proxy_date'
        }, format='%Y-%m-%d'),
        label='Дата доверенности',
        required=False
    )

    class Meta:
        model = User
        fields = ('full_name', 'position', 'email', 'role', 'iin', 'phone_number', 'proxy_number', 'proxy_date')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proxy_number'].required = False
        self.fields['proxy_date'].required = False 