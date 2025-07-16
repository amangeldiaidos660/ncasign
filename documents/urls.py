from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('gph/', views.gph_list, name='gph_list'),
    path('gph/create/', views.gph_create, name='gph_create'),
    path('gph/preview/', views.gph_preview, name='gph_preview'),
    path('gph/save/', views.gph_save, name='gph_save'),
    path('acts/', views.act_list, name='act_list'),
    path('acts/create/', views.act_create, name='act_create'),
    path('acts/preview/', views.act_preview, name='act_preview'),
    path('acts/download/', views.act_download, name='act_download'),
    path('acts/save/', views.act_save, name='act_save'),
    # Новые маршруты для работы с пакетами
    path('acts/add-to-package/', views.add_act_to_package, name='add_act_to_package'),
    path('acts/save-package/', views.save_package, name='save_package'),
    path('acts/clear-package/', views.clear_package, name='clear_package'),
    path('acts/package-info/', views.get_package_info, name='get_package_info'),
    path('api/pending-approvals/', views.api_pending_approvals, name='api_pending_approvals'),
    path('api/user-history/', views.api_user_history, name='api_user_history'),
    path('api/approve-action/', views.api_approve_action, name='api_approve_action'),
    path('api/approve-package/', views.api_approve_package, name='api_approve_package'),
] 