from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime

class User(AbstractUser):
    ROLE_CHOICES = [
        (1, 'Админ'),
        (2, 'Подписант'),
        (3, 'Согласующий'),
        (4, 'Исполнитель'),
        (5, 'Редактор'),
    ]
    
    username = models.CharField(max_length=254, primary_key=True, verbose_name='Username')
    full_name = models.CharField(max_length=100, verbose_name='ФИО')
    position = models.CharField(max_length=100, verbose_name='Должность')
    role = models.IntegerField(choices=ROLE_CHOICES, default=4, verbose_name='Роль')
    email = models.EmailField(unique=True, verbose_name='Email')
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name', 'position']
    
    def get_full_name(self):
        return self.full_name
    
    def save(self, *args, **kwargs):
        if not self.username:
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
            
            self.username = f"{current_year}{new_number:04d}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.get_full_name()
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        db_table = 'users' 