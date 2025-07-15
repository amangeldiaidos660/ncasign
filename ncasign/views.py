from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from ncasign.forms import CustomAuthenticationForm, CustomUserCreationForm, UserEditForm
from ncasign.models import User

# Универсальный декоратор для проверки ролей
from functools import wraps

def role_required(roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role not in roles:
                return redirect('index')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def index(request):
    return render(request, 'index.html')

def auth_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('profile')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'forms/auth.html', {'form': form})

from django.core.paginator import Paginator
from django.db.models import Q

@login_required
def admin_panel(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_panel')
    else:
        form = CustomUserCreationForm()
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        users = User.objects.filter(
            Q(username__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(position__icontains=search_query)
        )
    else:
        users = User.objects.all()
    # Пагинация
    per_page = request.GET.get('per_page', 20)
    paginator = Paginator(users, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/panel.html', {
        'form': form,
        'users': page_obj,
        'search_query': search_query,
        'per_page': per_page
    })

@login_required
@role_required([1])  # Только Админ
def create_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_panel')
    else:
        form = CustomUserCreationForm()
    return render(request, 'admin/create_user.html', {
        'form': form
    })

@login_required
@role_required([1])  # Только Админ
def edit_user(request, user_id):
    try:
        user = User.objects.get(username=user_id)
    except User.DoesNotExist:
        return redirect('admin_panel')
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('admin_panel')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'admin/edit_user.html', {
        'form': form,
        'user': user
    })

@login_required
@role_required([1])  # Только Админ
def delete_user(request, user_id):
    try:
        user = User.objects.get(username=user_id)
        if user.username != request.user.username:  # Нельзя удалить самого себя
            user.delete()
    except User.DoesNotExist:
        pass
    return redirect('admin_panel')

@login_required
def profile(request):
    return render(request, 'profile.html', {'user': request.user})

@login_required
def history(request):
    return render(request, 'history.html', {'user': request.user}) 