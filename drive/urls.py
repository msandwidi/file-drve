from django.urls import path
from . import views

urlpatterns = [
    path('', views.my_drive_view, name='my-box'),
    path('file/<int:file_id>/details', views.file_details_view, name='file-details'),
]