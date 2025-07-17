from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('proxy_number', 'proxy_date')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('proxy_number', 'proxy_date')}),
    )
    list_display = ('username', 'full_name', 'email', 'role', 'iin', 'phone_number', 'proxy_number', 'proxy_date', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'full_name', 'email', 'iin', 'phone_number', 'proxy_number')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')

admin.site.register(User, UserAdmin) 