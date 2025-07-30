from django.urls import path
from . import views

urlpatterns = [
    path('', views.my_drive_view, name='my-box'),
    path('fichiers-recents', views.my_drive_view, name='recent-files'),
    path('corbeille', views.trash_bin_view, name='my-trash'),
    path('file/<int:file_id>/details', views.file_details_view, name='file-details'),
]