from django.contrib import admin
from .models import FileRecord, FolderRecord

# Register your models here.
admin.site.register(FolderRecord)
admin.site.register(FileRecord)