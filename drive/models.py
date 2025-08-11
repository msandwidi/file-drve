from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils import timezone
from django.db import models
import uuid
import os

INVALID_FOLDER_CHARS = r'[^a-zA-Z0-9 _\-]+' 
RESERVED_NAMES = {'.', '..', 'con', 'nul', 'prn'}
MAX_FOLDER_DEPTH = 10
FOLDER_SIZE_30MB = 30 * 1024 * 1024
MAX_FILENAME_LENGTH = 255
MAX_SLUG_LENGTH = 255

def generate_slug(instance, is_folder = False):
    """
    Generate file slug
    """

    slug_candidate = None

    if is_folder:
        base_slug = slugify(instance.name)
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        slug_candidate = f"{base_slug}-{timestamp}"

        if len(slug_candidate) > MAX_SLUG_LENGTH:
            base_slug = base_slug[:MAX_SLUG_LENGTH - len(timestamp) - 1]  
            slug_candidate = f"{base_slug}-{timestamp}"

    else:
        base, ext = os.path.splitext(instance.name)
        base_slug = slugify(base)
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        
        # clean extension
        ext = ext.lower().lstrip('.')
        
        slug_candidate = f"{base_slug}-{timestamp}-{ext}"

        # Truncate if it's too long
        if len(slug_candidate) > MAX_SLUG_LENGTH:
            base_slug = base_slug[:MAX_SLUG_LENGTH - len(timestamp) - len(ext) - 2]
            slug_candidate = f"{base_slug}-{timestamp}"

    return slug_candidate

def sizeof_fmt(num, suffix="B"):
    """
    Get size of a file
    """
    
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Y{suffix}"

def user_hashed_upload_to(instance, filename):
    user_id = instance.user.id
    file_uuid = instance.file_uuid

    hex_str = file_uuid.hex
    root_folder = 'uploads'
    folder_1 = hex_str[:2]
    folder_2 = hex_str[2:4]
    extension = 'dat'
    filename = f"{hex_str}.{extension}"
    path = os.path.join(root_folder, f"u{user_id}", folder_1, folder_2, filename)

    return path

class FileRecord(models.Model):
    file = models.FileField(upload_to=user_hashed_upload_to)
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True, max_length=1500)

    file_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    is_shared = models.BooleanField(default=False)
    shared_at = models.DateTimeField(null=True, blank=True)
    shared_uuid = models.UUIDField(default=uuid.uuid4, unique=True)

    download_limit = models.IntegerField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)

    last_accessed_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    last_updated_at = models.DateTimeField(auto_now_add=True)
    
    expires_at = models.DateTimeField(null=True, blank=True)

    is_favorite = models.BooleanField(default=False)
    
    folder = models.ForeignKey(
        'drive.FolderRecord', 
        on_delete=models.SET_NULL, 
        related_name='files',
        null=True,
        blank=True,
    )
    
    user = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE, 
        related_name='files'
    )
    
    @property
    def size(self):
        if self.file and hasattr(self.file, 'path'):
            try:
                size_bytes = os.path.getsize(self.file.path)
                return size_bytes
            except OSError:
                return 0
        return 0
    
    @property
    def file_extension(self):
        name = self.name
        return os.path.splitext(name)[1].lower().lstrip('.')
    
    @property
    def display_name(self):
        return self.name
    
    @property
    def type(self):
        return 'file'
    
    @property
    def display_type(self):
        return self.file_extension
    
    @property
    def display_type_group(self):
        ext = self.display_type.lower()

        categories = {
            'pdf': ['pdf'],
            'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'tiff'],
            'document': ['pdf', 'doc', 'docx', 'odt', 'rtf', 'txt', 'md'],
            'spreadsheet': ['xls', 'xlsx', 'csv', 'ods'],
            'presentation': ['ppt', 'pptx', 'odp'],
            'archive': ['zip', 'rar', '7z', 'tar', 'gz'],
            'audio': ['mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a'],
            'video': ['mp4', 'webm', 'mov', 'avi', 'mkv', 'wmv', 'flv'],
        }

        for category, extensions in categories.items():
            if ext in extensions:
                return category

        return 'other'
    
    @property
    def display_size(self):
        return sizeof_fmt(self.size)
    
    @property
    def name_without_ext(self):
        return os.path.splitext(self.name)[0]

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} by {self.user.username}"

    def is_expired(self):
        from django.utils import timezone
        return self.expires_at and timezone.now() > self.expires_at

    def save(self, *args, **kwargs):

        slug_candidate = generate_slug(self)

        if self.slug != slug_candidate:
            self.slug = slug_candidate

        super().save(*args, **kwargs)

class FolderRecord(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True, blank=True)
    
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    is_shared = models.BooleanField(default=False)
    shared_at = models.DateTimeField(null=True, blank=True)
    shared_uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    expires_at = models.DateTimeField(null=True, blank=True)
    
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    is_favorite = models.BooleanField(default=False)
    
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
    
    @property
    def display_size(self):
        """
        Human readable format
        """
        total_size = self.get_size()

        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if total_size < 1024:
                return f"{total_size:.2f} {unit}"
            total_size /= 1024
        return f"{total_size:.2f} PB"

    @property
    def display_name(self):
        return self.name
    
    @property
    def type(self):
        return 'folder'
    
    @property
    def display_type(self):
        return 'dossier'

    def rename_folder(self, new_name, desc):
        base_slug = slugify(new_name)
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        slug_candidate = f"{base_slug}-{timestamp}"

        if len(slug_candidate) > MAX_SLUG_LENGTH:
            base_slug = base_slug[:MAX_SLUG_LENGTH - len(timestamp) - 1]  
            slug_candidate = f"{base_slug}-{timestamp}"

        self.slug = slug_candidate
        self.description = desc
        self.name = new_name
        
        self.save()
    
    def is_over_30mb(self):
        return self.get_size() >= FOLDER_SIZE_30MB
        
    def get_size(self):
        """
        Get folder size
        """
        total = 0

        # Sum sizes of files directly in this folder
        for f in self.files.filter(is_deleted=False):
            if f.file:
                total += f.file.size

        # Recurse into subfolders
        for subfolder in self.subfolders.filter(is_deleted=False):
            total += subfolder.get_size()

        return total
    
    def get_depth(self):
        """
        Returns how deeply nested this folder is under the user's root.
        Root folder (parent=None) → depth 0
        One level under root → depth 1, and so on.
        """
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth
    
    def save(self, *args, **kwargs):
        slug_candidate = generate_slug(self, is_folder=True)

        if self.slug != slug_candidate:
            self.slug = slug_candidate

        super().save(*args, **kwargs)

    def is_expired(self):
        from django.utils import timezone
        return self.expires_at and timezone.now() > self.expires_at

    def full_path_data(self):
        parts = [{
            'id': self.id,
            'slug': self.slug,
            'name': self.name,
            'is_favorite': self.is_favorite,
        }]
        
        parent = self.parent
        
        while parent:
            
            parts.append(
            {
                'id': parent.id,
                'slug': parent.slug,
                'name': parent.name,
                'is_favorite': parent.is_favorite,
            })
            
            parent = parent.parent
            
        return reversed(parts)
    
    def full_path(self):
        parts = [self.name]
        parent = self.parent
        while parent:
            parts.append(parent.name)
            parent = parent.parent
        return "/" + "/".join(reversed(parts))    
