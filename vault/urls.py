from django.urls import path
from . import views

app_name = 'vault'

urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('v/push/', views.api_upload, name='api_upload'),
    path('processing/<str:vault_id>/', views.processing_view, name='processing'),
    path('qr/<str:vault_id>/', views.qr_result_view, name='qr_result'),
    path('access/<str:vault_id>/', views.access_file_view, name='access_file'),
]
