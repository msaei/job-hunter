from django.urls import path
from . import views

app_name = 'applications'
urlpatterns = [
    path('applications/export/csv/', views.export_csv, name='export_csv'),
    path('applications/import/csv/', views.import_csv, name='import_csv'),
    path('', views.ApplicationList.as_view(), name='list'),
    path('applications/new/', views.ApplicationCreate.as_view(), name='create'),
    path('applications/<int:pk>/', views.ApplicationDetail.as_view(), name='detail'),
    path('applications/<int:pk>/edit/', views.ApplicationUpdate.as_view(), name='edit'),
    path('applications/<int:pk>/attachments/', views.upload_attachment, name='upload_attachment'),
    path('applications/<int:pk>/attachments/<int:attachment_pk>/download/', views.download_attachment, name='download_attachment'),
    path('applications/<int:pk>/attachments/<int:attachment_pk>/remove/', views.remove_attachment, name='remove_attachment'),
]
