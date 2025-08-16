from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import Q
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
        folder_uuid = f'{instance.folder_uuid}'
        base_slug = slugify(f"{instance.name}-{folder_uuid[:5]}")
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
        slug_candidate = f"{base_slug}-{timestamp}"

        if len(slug_candidate) > MAX_SLUG_LENGTH:
            base_slug = slugify(instance.name)
            base_slug = base_slug[:MAX_SLUG_LENGTH - len(folder_uuid[:8]) - len(timestamp) - 2]  
            slug_candidate = f"{base_slug}-{folder_uuid[:8]}-{timestamp}"

    else:
        file_uuid = f'{instance.file_uuid}'
        base, ext = os.path.splitext(instance.name)
        base_slug = slugify(f"{base}-{file_uuid[:5]}")
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
        
        # clean extension
        ext = ext.lower().lstrip('.')
        
        slug_candidate = f"{base_slug}-{timestamp}-{ext}"

        # Truncate if it's too long
        if len(slug_candidate) > MAX_SLUG_LENGTH:
            base_slug = slugify(base)
            base_slug = base_slug[:MAX_SLUG_LENGTH - len(file_uuid[:8]) - len(timestamp) - len(ext) - 3]
            slug_candidate = f"{base_slug}-{file_uuid[:8]}-{timestamp}"

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
    
    is_favorite = models.BooleanField(default=False)

    @property
    def is_shared(self):
        # Check if the file itself is explicitly shared and not expired
        if self.shared_at and (not self.share_expires_at or self.share_expires_at > timezone.now()):
            return True

        # Check parent folders
        folder = self.folder
        while folder:
            if folder.shared_at and (not folder.share_expires_at or folder.share_expires_at > timezone.now()):
                return True
            folder = folder.parent

        return False

    shared_at = models.DateTimeField(null=True, blank=True)
    share_expires_at = models.DateTimeField(null=True, blank=True)
    shared_uuid = models.UUIDField(default=uuid.uuid4, unique=True)

    download_limit = models.IntegerField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    last_updated_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    folder = models.ForeignKey(
        'FolderRecord', 
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
    
    def active_direct_shares(self):
        shares = self.shares.all()
        return shares.filter(is_deleted = False)
    
    def get_all_parent_folders(self):
        parents = []
        folder = self.folder
        
        while folder is not None and not folder.is_deleted:
            parents.append(folder)
            folder = folder.parent
        return parents
    
    def get_all_shared_parents(self):
        parents = []
        folder = self.folder
        
        while folder is not None and not folder.is_deleted:
            if folder.is_shared:
                parents.append(folder)
            folder = folder.parent
        return parents
    
    def is_accessible_by_user(self, user):
        """
        Check if the file is directly shared with the user
        or if any of its parent folders is shared with the user.
        """
        # 1. Check if file is directly shared with the user
        if self.shares.filter(is_deleted=False, contact__user=user).exists():
            return True

        # 2. Check if any parent folder is shared with the user
        folder = self.folder
        while folder is not None and not folder.is_deleted:
            if folder.shares.filter(is_deleted=False, contact__user=user).exists():
                return True
            folder = folder.parent
        
        return False

    def get_users_with_access(self):
        parents = self.get_all_parent_folders()
        
        User = get_user_model()

        return User.objects.filter(
            Q(contacts__shared_items__file=self) |
            Q(shared_items__file=self) |
            Q(contacts__shared_items__folder__in=parents) |
            Q(shared_items__folder__in=parents),
            contacts__shared_items__is_deleted=False
        ).distinct()

    def get_contacts_with_access(self):
        # Get all parent folders of the file
        parents = self.get_all_parent_folders()

        return ContactDetails.objects.filter(
            Q(shared_items__file=self) |                 # Directly shared with the file
            Q(shared_items__folder__in=parents),        # Shared via any parent folder
            shared_items__is_deleted=False              # Only non-deleted shares
        ).distinct()
        
    def get_share_records_with_access(self):
        """
        Return all ShareRecord instances that give access to this file,
        including shares on the file itself and shares on any parent folder.
        """
        # Get all parent folders
        parents = self.get_all_parent_folders()

        return ShareRecord.objects.filter(
            Q(file=self) |
            Q(folder__in=parents),
            is_deleted=False
        ).select_related('contact', 'recipient').distinct()
        
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} by {self.user.username}"

    def is_expired(self):
        from django.utils import timezone
        return self.expires_at and timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        
        slug_candidate = generate_slug(self)
        
        if not self.pk:
            # New record → always generate slug
            self.slug = slug_candidate
            
        else:
            # Existing record → check if name changed
            original = type(self).objects.get(pk=self.pk)
            if original.name != self.name:
                self.slug = slug_candidate

            if not original.is_deleted and self.is_deleted:
                # Mark related shares as deleted
                self.shares.update(is_deleted=True, deleted_at=timezone.now())

        super().save(*args, **kwargs)

class FolderRecord(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True, blank=True)
    
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    folder_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    is_favorite = models.BooleanField(default=False)

    @property
    def is_shared(self):
        # Check if the file itself is explicitly shared and not expired
        if self.shared_at and (not self.share_expires_at or self.share_expires_at > timezone.now()):
            return True

        # Check parent folders
        folder = self.parent
        while folder:
            if folder.shared_at and (not folder.share_expires_at or folder.share_expires_at > timezone.now()):
                return True
            folder = folder.parent

        return False
    
    shared_at = models.DateTimeField(null=True, blank=True)
    share_expires_at = models.DateTimeField(null=True, blank=True)
    shared_uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
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
    
    def active_direct_shares(self):
        shares = self.shares.all()
        return shares.filter(is_deleted = False)
    
    def get_all_parent_folders(self):
        parents = []
        folder = self.parent
        
        while folder is not None and not folder.is_deleted:
            parents.append(folder)
            folder = folder.parent
        return parents
    
    def get_all_shared_parents(self):
        parents = []
        folder = self.parent
        
        while folder is not None and not folder.is_deleted:
            if folder.is_shared:
                parents.append(folder)
            folder = folder.parent
        return parents
    
    def is_accessible_by_user(self, user):
        """
        Check if the file is directly shared with the user
        or if any of its parent folders is shared with the user.
        """
        # 1. Check if file is directly shared with the user
        if self.shares.filter(is_deleted=False, contact__user=user).exists():
            return True

        # 2. Check if any parent folder is shared with the user
        folder = self.parent
        while folder is not None and not folder.is_deleted:
            if folder.shares.filter(is_deleted=False, contact__user=user).exists():
                return True
            folder = folder.parent
        
        return False

    def get_users_with_access(self):
        parents = self.get_all_parent_folders()
        
        User = get_user_model()

        return User.objects.filter(
            Q(contacts__shared_items__folder=self) |
            Q(shared_items__folder=self) |
            Q(contacts__shared_items__folder__in=parents) |
            Q(shared_items__folder__in=parents),
            contacts__shared_items__is_deleted=False
        ).distinct()
        
    def get_contacts_with_access(self):
        # Get all parent folders of the file
        parents = self.get_all_parent_folders()

        return ContactDetails.objects.filter(
            Q(shared_items__folder=self) |                 # Directly shared with the file
            Q(shared_items__folder__in=parents),        # Shared via any parent folder
            shared_items__is_deleted=False              # Only non-deleted shares
        ).distinct()
    
    def get_share_records_with_access(self):
        """
        Return all ShareRecord instances that give access to this file,
        including shares on the file itself and shares on any parent folder.
        """
        # Get all parent folders
        parents = self.get_all_parent_folders()

        return ShareRecord.objects.filter(
            Q(folder=self) |
            Q(folder__in=parents),
            is_deleted=False
        ).select_related('contact', 'recipient').distinct()

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
        
        if not self.pk:
            # New record → always generate slug
            self.slug = slug_candidate
            
        else:
            # Existing record → check if name changed
            original = type(self).objects.get(pk=self.pk)
            if original.name != self.name:
                self.slug = slug_candidate
            
            if not original.is_deleted and self.is_deleted:
                # Mark related shares as deleted
                self.shares.update(is_deleted=True, deleted_at=timezone.now())

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

class ShareRecord(models.Model):
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    shared_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    contact = models.ForeignKey(
        'ContactDetails', 
        on_delete=models.CASCADE, 
        related_name='shared_items',
    )
    
    recipient = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE, 
        related_name='shared_items',
        blank=True,
        null=True
    )

    file = models.ForeignKey(
        'FileRecord', 
        null=True,
        blank=True,
        on_delete=models.CASCADE, 
        related_name='shares'
    )

    folder = models.ForeignKey(
        'FolderRecord',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='shares'
    )
    
    def __str__(self):
        name = ''
        
        if self.file:
            name = self.file.name
        else:
            name = self.folder.name
            
        return f"{self.contact.full_name} - {name}"
        
    def save(self, *args, **kwargs):
        
        if self.folder:
            slug_candidate = generate_slug(self.folder, is_folder=True)
            
        elif self.file:
            slug_candidate = generate_slug(self.file, is_folder=True)
        
        if not self.pk:
            # New record → always generate slug
            self.slug = slug_candidate
            
        else:
            # Existing record → check if name changed
            original = type(self).objects.get(pk=self.pk)
            if original.file and original.file != self.file.name:
                self.slug = slug_candidate
            
            elif original.folder and original.folder != self.folder.name:
                self.slug = slug_candidate

        super().save(*args, **kwargs)

class ContactDetails(models.Model):

    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()

    created_at = models.DateTimeField(auto_now_add=True)

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    is_imported = models.BooleanField(default=False)
    imported_at = models.DateTimeField(null=True, blank=True)
    imported_contact_id = models.PositiveBigIntegerField(null=True, blank=True)

    groups = models.ManyToManyField(
        'ContactGroup',  
        related_name='contacts',
        blank=True
    )

    user = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE, 
        related_name='contacts'
    )
    
    class Meta:
        ordering = ['first_name']

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class ContactGroup(models.Model):

    name = models.CharField(max_length=255)
    description = models.TextField(max_length=1500)

    created_at = models.DateTimeField(auto_now_add=True)

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    user = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE, 
        related_name='contact_groups'
    )
    
    class Meta:
        ordering = ['name']

    @property
    def full_name(self):
        return f"{self.name} {self.user.username}"
    
    def __str__(self):
        return self.name
