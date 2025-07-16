from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from ncasign.models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'position', 'role', 'iin', 'phone_number')
    search_fields = ('full_name', 'email', 'iin', 'phone_number')
    list_filter = ('role',)
    ordering = ('full_name',)
    
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Персональная информация', {'fields': ('full_name', 'position', 'role', 'iin', 'phone_number')}),
        ('Разрешения', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'full_name', 'position', 'role', 'iin', 'phone_number', 'password1', 'password2'),
        }),
    ) 