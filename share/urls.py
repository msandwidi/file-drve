from django.urls import path
from . import views

urlpatterns = [
    path('<slug:slug>', views.shared_item_details, name='shared-item-details'),
    path('dossier/<slug:slug>/delete', views.delete_shared_item_view, name='delete-shared-item'),
    
    # folder
    path('dossier/<slug:slug>', views.shared_folder_details, name='shared-folder-details'),
    path('dossier/<slug:slug>/copier', views.copy_shared_folder_view, name='copy-shared-folder'),
    path('dossier/<slug:slug>/download', views.download_shared_folder_view, name='download-shared-folder'),
    
    # file
    path('fichier/<slug:slug>', views.shared_file_details, name='shared-file-details'),
    path('fichier/<slug:slug>/copier', views.copy_shared_file_view, name='copy-shared-file'),
    path('fichier/<slug:slug>/view', views.view_shared_file_content_view, name='view-shared-file'),
    path('fichier/<slug:slug>/download', views.download_shared_file_view, name='download-shared-file'),
]