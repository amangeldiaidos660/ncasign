from django.urls import path
from . import views

urlpatterns = [
    path('gph/', views.gph_list, name='signers_gph_list'),
    path('acts/', views.act_list, name='signers_act_list'),
    path('package-docx/<str:package_id>/', views.package_docx, name='package_docx'),
    path('wait-sign/', views.wait_sign_list, name='signers_wait_sign'),
    path('sign/<str:doc_type>/<str:doc_id>/', views.sign_document, name='sign_document'),
    path('approve/<str:doc_type>/<str:doc_id>/', views.approve_document, name='approve_document'),
    path('reject/<str:doc_type>/<str:doc_id>/', views.reject_document, name='reject_document'),
    path('upload/<str:doc_type>/<str:doc_id>/', views.upload_files, name='upload_files'),
    path('approve-package/<str:package_id>/', views.approve_package, name='approve_package'),
    path('sign-package/<str:package_id>/', views.sign_package, name='sign_package'),
    path('reject-package/<str:package_id>/', views.reject_package, name='reject_package'),
] 