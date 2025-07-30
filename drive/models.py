from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils import timezone
from django.db import models
import uuid
import os

def user_directory_path(instance, filename):
    base, ext = os.path.splitext(filename)
    safe_name = slugify(base)  
    
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    final_name = f"{timestamp}_{safe_name}{ext.lower()}"

    if instance.folder:
        folder_path = instance.folder.full_path()
        return f'user_{instance.user.id}/{folder_path}/{final_name}'
    return f'user_{instance.user.id}/{final_name}'

class FileRecord(models.Model):
    file = models.FileField(upload_to=user_directory_path)

    original_filename = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    is_public = models.BooleanField(default=False)
    shared_uuid = models.UUIDField(default=uuid.uuid4, unique=True)

    download_limit = models.IntegerField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)

    last_accessed_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    expires_at = models.DateTimeField(null=True, blank=True)
    
    folder = models.ForeignKey(
        'drive.FolderRecord', 
        on_delete=models.SET_NULL, 
        related_name='folder',
        null=True,
        blank=True,
    )
    
    user = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE, 
        related_name='files'
    )
    
    @property
    def file_extension(self):
        name = self.file.name
        return os.path.splitext(name)[1].lower().lstrip('.')

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_filename} by {self.user.username}"

    def is_expired(self):
        from django.utils import timezone
        return self.expires_at and timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        # Save original filename
        if not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

class FolderRecord(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True, blank=True)
    
    is_public = models.BooleanField(default=False)
    shared_uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    expires_at = models.DateTimeField(null=True, blank=True)
    
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    user = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE, 
        related_name='folders'
    )
    
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='subfolders'
    )

    class Meta:
        unique_together = ('user', 'parent', 'name')  # prevent duplicate folder names within same parent
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
    def is_expired(self):
        from django.utils import timezone
        return self.expires_at and timezone.now() > self.expires_at

    def full_path(self):
        parts = [self.name]
        parent = self.parent
        while parent:
            parts.append(parent.name)
            parent = parent.parent
        return '/'.join(reversed(parts))