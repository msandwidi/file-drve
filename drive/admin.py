from django.contrib import admin
from .models import (
    FileRecord, 
    FolderRecord, 
    ShareRecord, 
    ContactDetails,
    ContactGroup,
    UserNotification
)

# Register your models here.
admin.site.register(FolderRecord)
admin.site.register(FileRecord)
admin.site.register(ShareRecord)
admin.site.register(ContactDetails)
admin.site.register(ContactGroup)
admin.site.register(UserNotification)