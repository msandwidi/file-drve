from django.urls import path
from . import views

urlpatterns = [
    path('<slug:slug>', views.shared_item_details, name='shared-item-details'),
    path('fichier/<slug:slug>', views.shared_file_details, name='shared-file-details'),
    path('dossier/<slug:slug>', views.shared_folder_details, name='shared-folder-details'),
    path('fichier/<slug:slug>/view', views.view_shared_file_content_view, name='view-shared-file'),
    path('fichier/<slug:slug>/download', views.download_shared_file_view, name='download-shared-file'),
    path('fichier/<slug:slug>/delete', views.delete_shared_file_view, name='delete-shared-file'),
    path('fichier/<slug:slug>/copier', views.copy_shared_file_view, name='copy-shared-file'),
]