"""
URL configuration for ncasign project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('login/', views.auth_view, name='auth'),
    path('admin/panel/', views.admin_panel, name='admin_panel'),
    path('admin/create/', views.create_user, name='create_user'),
    path('admin/edit/<str:user_id>/', views.edit_user, name='edit_user'),
    path('admin/delete/<str:user_id>/', views.delete_user, name='delete_user'),
    path('documents/', include('documents.urls')),
    path('profile/', views.profile, name='profile'),
    path('history/', views.history, name='history'),
    path('root/', admin.site.urls),
    path('', views.index, name='index'),
]
