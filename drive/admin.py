from django.contrib import admin
from .models import FileRecord, FolderRecord, ShareRecord, ContactRecord

# Register your models here.
admin.site.register(FolderRecord)
admin.site.register(FileRecord)
admin.site.register(ShareRecord)
admin.site.register(ContactRecord)