from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from ncasign.models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('full_name', 'email', 'position', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('full_name', 'email', 'position')
    ordering = ('full_name',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Персональная информация', {'fields': ('full_name', 'position', 'role')}),
        ('Разрешения', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'position', 'role', 'password1', 'password2'),
        }),
    ) 