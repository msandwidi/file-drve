from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from .models import FileRecord, FolderRecord
from django.core.paginator import Paginator
from django.contrib import messages
from core.utils import is_valid_int
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

ALLOWED_FILE_SIZE = 10 * 1024 * 1024
MAX_TOTAL_UPLOAD_SIZE = 20 * 1024 * 1024 
MAX_FILES_COUNT = 20
MAX_FILES_COUNT_PER_DAY = 80
MAX_FILES_COUNT_PER_HOUR = 50

def my_drive_view(request):
    """
    Get all user files
    """
    
    page_size = request.GET.get('page_size', '20')
    if is_valid_int(page_size):
        page_size = int(page_size)
    else:
        page_size = 20
    
    page = request.GET.get('page', '1')
    if is_valid_int(page):
        page = int(page) 
    else:
        page = 1
        
    folder_slug = request.GET.get('dossier')
    
    folder = None
    files=list()
    folders=list()
        
    if folder_slug == 'fichiers-recents':
        # recent files
        logger.info(f'fetching {folder_slug}...')

        files = FileRecord.objects.filter(
            user=request.user,
            is_deleted=False,
        ).order_by('-last_accessed_at')

        # always return empty result
        folders = FolderRecord.objects.none()

    elif folder_slug == 'favoris':
        # favorite folders
        logger.info(f'fetching {folder_slug}...')

        files = FileRecord.objects.filter(
            user=request.user,
            is_deleted=False,
            is_favorite=True,
        )

        # favorite folders
        folders = FolderRecord.objects.filter(
            is_deleted=False,
            user=request.user,
            is_favorite=True,
        )

    elif folder_slug == 'partages':
        # shared folders
        logger.info(f'fetching {folder_slug}...')

        files = FileRecord.objects.filter(
            user=request.user,
            is_deleted=False,
            is_shared=True,
        )

        # shared folders
        folders = FolderRecord.objects.filter(
            is_deleted=False,
            user=request.user,
            is_shared=True,
        )
        
    elif folder_slug == 'partages-avec-moi':
        # files shared with me
        logger.info(f'fetching {folder_slug}...')

        files = FileRecord.objects.filter(
            user=request.user,
            is_deleted=False,
            is_shared=True,
        ).exclude(user=request.user)

        # folders shared with me
        folders = FolderRecord.objects.filter(
            is_deleted=False,
            user=request.user,
            is_shared=True,
        ).exclude(user=request.user)
    
    elif folder_slug:
        logger.info('Finding folder by slog...')

        folder = FolderRecord.objects.filter(
            slug=folder_slug,
            user=request.user,
            is_deleted=False,
        ).first()

        if not folder:
            messages.warning(request, 'Dossier introuvable')
            return redirect('my-box')
        
        logger.info(f'fetching folder {folder_slug} content...')

        files = folder.files.all()
        
        folders = folder.subfolders.all().filter(is_deleted=False)

    else:
        logger.info(f'fetching root folders and files...')

        # root files
        files = FileRecord.objects.filter(
            user=request.user,
            is_deleted=False,
            folder=None
        )

        # root folders
        folders = FolderRecord.objects.filter(
            is_deleted=False,
            user=request.user,
            parent=None
        )
                        
    items = list(folders) + list(files)
        
    paginator = Paginator(items, page_size) 
    page_obj = paginator.get_page(page)
    
    return render(request, 'drive/my-drive.html', {
        'files': page_obj,
        'folders': folders,
        'folder': folder,
        'folder_slug': folder_slug,
        'page_data': page_obj,
        'recent_folders': folders.order_by('-created_at')[:10]
    })

def file_details_view(request, slug):
    """
    Get file details
    """
    
    file = FileRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        user=request.user
    ).first()
    
    if not file:
        messages.warning(request, 'Fichier introuvable')
        return redirect('my-box')

    return render(request, 'file/file-details.html', {
        'file': file
    })

def delete_folder_view(request, slug):
    """
    Delete folder
    """
    
    folder = FolderRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        user=request.user
    ).first()
    
    if not folder:
        messages.warning(request, 'Dossier introuvable')
        return redirect('my-box')
    
    parent = folder.parent
    
    if not folder.files.all():
        # hard delete empty folders
        folder.delete()

    else:
        # soft delete non-empty folders
        folder.is_deleted = True
        folder.deleted_at = timezone.now()

        folder.save()
    
    messages.success(request, 'Dossier supprimeé')

    if parent:
        url = reverse('my-box')
        return redirect(f"{url}?dossier={parent.slug}")

    return redirect('my-box')

def delete_file_view(request, slug):
    """
    Delete file
    """
    
    file = FileRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        user=request.user
    ).first()
    
    if not file:
        messages.warning(request, 'Fichier introuvable')
        return redirect('my-box')
    
    parent = file.folder
    
    file.is_deleted = True
    file.deleted_at = timezone.now()
    file.save()
    
    messages.success(request, 'Fichier supprimé')

    if parent:
        url = reverse('my-box')
        return redirect(f"{url}?dossier={parent.slug}")

    return redirect('my-box')

def share_folder_view(request, slug):
    """
    Share folder
    """
    
    folder = FolderRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        user=request.user
    ).first()
    
    if not folder:
        messages.warning(request, 'Dossier introuvable')
        return redirect('my-box')
    
    if request.method == 'POST':

        if hasattr(folder, "is_shared"):
            folder.is_shared = True
            folder.shared_at = timezone.now()
            folder.save(update_fields=["is_shared", 'shared_at'])
    
            messages.success(request, 'Dossier partagé')

            return redirect('share-folder', slug=slug)
        
    folders = folder.subfolders.all()
    files = folder.files.all()
        
    items = list(folders) + list(files)
        
    paginator = Paginator(items, 20) 
    page_obj = paginator.get_page(1)

    return render(request, 'drive/share-folder.html', {
        'folder': folder,
        'items': page_obj
    })

@require_http_methods(['GET'])
def toggle_favorite_view(request, slug):
    """
    Toggle favorite file or folder
    """
    slug_type = request.GET.get('type')
    folder_slug = request.GET.get('dossier')

    file = None

    if slug_type == 'folder':

        folder = FolderRecord.objects.filter(
            slug=slug,
            user=request.user,
            is_deleted=False,
        ).first()

        if folder and hasattr(folder, "is_favorite"):
            folder.is_favorite = not folder.is_favorite
            folder.save(update_fields=["is_favorite"])

            logger.info('toggled favorite folder')  

            messages.success(request, 'Dossier marqué favoris')
        
    else:

        file = FileRecord.objects.filter(
            slug=slug,
            is_deleted=False,
            user=request.user
        ).first()
        
        if file and hasattr(file, "is_favorite"):
            file.is_favorite = not file.is_favorite
            file.save(update_fields=["is_favorite"])
    
            logger.info('toggled favorite file')

            messages.success(request, 'Fichier marqué favoris')

    url = reverse('my-box')

    if folder_slug:
        return redirect(f"{url}?dossier={folder_slug}")
    
    elif file and file.folder:
        return redirect(f"{url}?dossier={file.folder.slug}")
    
    return redirect('my-box')

@require_http_methods(['POST'])
def create_folder_view(request):
    """
    Create a new folder
    """
    
    slug = request.GET.get('dossier')
    folder = None
    
    if slug:
        folder = FolderRecord.objects.filter(
            user=request.user,
            is_deleted=False,
            slug=slug
        ).first()
        
        if not folder:
            messages.warning(request, 'Dossier introuvable')
            return redirect('my-box')
        
    name = request.POST.get('name')
    
    if not name:
        messages.warning(request, 'Erreur')
        return redirect('my-box')
    
    description = request.POST.get('description')
    
    new_folder = FolderRecord.objects.create(
        name=name,
        description=description,
        parent=folder,
        user=request.user
    )
    
    url = reverse('my-box')

    if folder:
        return redirect(f"{url}?dossier={folder.slug}")
    return redirect(f"{url}?dossier={new_folder.slug}")
    
@require_http_methods(['POST'])
def upload_files_view(request):
    """
    Upload files
    """
    
    folder_slug = request.GET.get('dossier')
    folder = None
    
    if folder_slug:
        
        folder = FolderRecord.objects.filter(
            slug=folder_slug,
            user=request.user,
            is_deleted=False,
        ).first()
        
        if not folder:
            
            messages.warning(request, 'Dossier introuvalbe')
            return redirect('my-box')
    
    uploaded_file = request.FILES.get('file')
    files = request.FILES.getlist('file')
    
    user = request.user
    now = timezone.now()

    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)

    last_hour_count = FileRecord.objects.filter(
        user=user,
        created_at__gte=one_hour_ago
    ).count()

    last_day_count = FileRecord.objects.filter(
        user=user,
        created_at__gte=one_day_ago
    ).count()

    if last_hour_count + len(files) > MAX_FILES_COUNT_PER_HOUR:
        messages.warning(request, f"Limite atteinte : {MAX_FILES_COUNT_PER_HOUR} fichiers maximum par heure")
        return redirect('my-box')
    
    if last_day_count + len(files) > MAX_FILES_COUNT_PER_DAY:
        messages.warning(request, F"Limite atteinte : {MAX_FILES_COUNT_PER_DAY} fichiers maximum par heure")
        return redirect('my-box')
    
    # Count files
    num_files = len(files)

    # Total size in bytes
    total_size = sum(f.size for f in files)
    
    # Optional limits
    if num_files > MAX_FILES_COUNT:
        return ValidationError("Too many files. Max is 5.")

    if total_size > 20 * 1024 * 1024:  # e.g., 20 MB
        return ValidationError("Total file size exceeds 20MB.")

    
    for uploaded_file in files:
        
        # allowed file size
        if uploaded_file.size > ALLOWED_FILE_SIZE:
            raise ValidationError("File too large")

        # allowed extensions
        if not uploaded_file.name.lower().endswith(('.pdf', '.jpg', '.zip')):
            raise ValidationError("Unsupported file type")

        file_record = FileRecord.objects.create(
            user=user,
            file=uploaded_file,
            folder=folder
        )
        
    messages.success(request, 'Ficher sauvegardé')
    
    url = reverse('my-box')

    if folder_slug:
        return redirect(f"{url}?dossier={folder_slug}")
    
    return redirect('my-box')  

def trash_bin_view(request):
    """
    View deleted files
    """
    
    files = FileRecord.objects.filter(
        user=request.user,
        is_deleted=True
    ).order_by('-deleted_at')
    
    return render(request, 'drive/trash-bin.html', {
        'files': files[:50]
    })