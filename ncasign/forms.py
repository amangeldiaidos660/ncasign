from django import forms
from django.contrib.auth.forms import AuthenticationForm
from ncasign.models import User
from datetime import datetime

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
            # Проверяем, является ли поле email
            if '@' in username:
                # Ищем пользователя по email
                try:
                    user = User.objects.get(email=username)
                    return user.username
                except User.DoesNotExist:
                    raise forms.ValidationError('Пользователь с таким email не найден')
            else:
                # Используем как username (ID)
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
        })
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

    class Meta:
        model = User
        fields = ('full_name', 'position', 'role', 'email')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Генерируем username как год + порядковый номер (YY####)
        current_year = str(datetime.now().year)[2:]  # 25 для 2025
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


class UserEditForm(forms.ModelForm):
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
        })
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

    class Meta:
        model = User
        fields = ('full_name', 'position', 'role', 'email') 