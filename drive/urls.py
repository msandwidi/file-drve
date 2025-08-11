from django.urls import path
from . import views

urlpatterns = [
    path('', views.my_drive_view, name='my-box'),
    path('corbeille', views.trash_bin_view, name='my-trash'),
    path('nouveau-dossier', views.create_folder_view, name='new-folder'),
    path('dossier/<slug:slug>/supprimer', views.delete_folder_view, name='delete-folder'),
    path('dossier/<slug:slug>/partager', views.share_folder_view, name='share-folder'),
    path('dossier/<slug:slug>/download', views.download_folder_view, name='download-folder'),
    path('dossier/<slug:slug>/rename', views.rename_folder_view, name='rename-folder'),
    path('fichier/<slug:slug>/partager', views.share_file_view, name='share-file'),
    path('fichier/<slug:slug>/rename/submit', views.rename_file_info_view, name='rename-file-info'),
    path('fichier/<slug:slug>/details', views.file_details_view, name='file-details'),
    path('fichier/<slug:slug>/view', views.view_file_content_view, name='view-file'),
    path('fichier/<slug:slug>/supprimer', views.delete_file_view, name='delete-file'),
    path('fichier/<slug:slug>/download', views.download_file_view, name='download-file'),
    path('fichier/importer', views.upload_files_view, name='upload-files'),
    path('favoris/<slug:slug>', views.toggle_favorite_view, name='toggle-favorite'),
]