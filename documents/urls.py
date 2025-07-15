from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('gph/', views.gph_list, name='gph_list'),
    path('gph/create/', views.gph_create, name='gph_create'),
    path('gph/preview/', views.gph_preview, name='gph_preview'),
    path('gph/save/', views.gph_save, name='gph_save'),
    path('acts/', views.acts_list, name='acts_list'),
    path('api/pending-approvals/', views.api_pending_approvals, name='api_pending_approvals'),
    path('api/approve-document/', views.api_approve_document, name='api_approve_document'),
    path('api/user-history/', views.api_user_history, name='api_user_history'),
] 