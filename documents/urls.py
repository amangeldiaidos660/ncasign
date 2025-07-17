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
    path('acts/add-to-package/', views.add_act_to_package, name='add_act_to_package'),
    path('acts/save-package/', views.save_package, name='save_package'),
    path('acts/clear-package/', views.clear_package, name='clear_package'),
    path('acts/package-info/', views.get_package_info, name='get_package_info'),
] 