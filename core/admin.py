from django.contrib import admin
from . import models as coreModels

# Register your models here.
admin.site.register(coreModels.ContactMessage)