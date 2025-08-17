from .models import FileRecord, FolderRecord, ShareRecord, ContactDetails, ContactGroup
from django.views.decorators.clickjacking import xframe_options_exempt
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .utils import is_safe_filename, is_safe_foldername
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.contrib import messages
from core.utils import is_valid_int
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from django.db.models import Q
import mimetypes
import logging
import zipfile
import os
import io

logger = logging.getLogger(__name__)

ALLOWED_FILE_SIZE = 10 * 1024 * 1024 # 10MB

MAX_TOTAL_UPLOAD_SIZE = 20 * 1024 * 1024 # 20MB

MAX_FILES_COUNT_PER_REQUEST = 20

MAX_FILES_COUNT_PER_DAY = 80 # 80 files per 24h

MAX_FILES_COUNT_PER_HOUR = 50 # 50 files per 1h

FORBIDDEN_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.sh', '.php', '.py', '.js', '.jar',
    '.pl', '.cgi', '.vb', '.asp', '.aspx', '.html', '.htm', '.svg',
    '.dll', '.iso', '.ps1', '.apk', '.chm'
}

def delete_folder_and_contents(folder):
    """
    Delete a folder and its content
    """

    if not folder.is_deleted:
    # Delete all files in this folder
        for file in folder.files.all():

            if not file.is_deleted:
                file.is_deleted = True
                file.deleted_at = timezone.now()
                file.shared_at = None
                file.save()

        # delete all subfolders
        for subfolder in folder.subfolders.all():
            delete_folder_and_contents(subfolder)

        # soft delete the folder
        folder.is_deleted = True
        folder.deleted_at = timezone.now()
        folder.shared_at = None
        folder.save()

def add_folder_to_zip(zip_file, folder, base_path):
    # Add files in this folder
    for file_record in folder.files.filter(is_deleted=False):
        if file_record.file:
            file_path = file_record.file.path
            arcname = os.path.join(base_path, file_record.name)
            zip_file.write(file_path, arcname=arcname)

    # Recurse into subfolders
    for subfolder in folder.subfolders.filter(is_deleted=False):
        sub_path = os.path.join(base_path, subfolder.name)
        add_folder_to_zip(zip_file, subfolder, sub_path)

def is_extension_safe(file):
    name, ext = os.path.splitext(file.name)
    if not ext:
        return False
    return ext.lower() not in FORBIDDEN_EXTENSIONS

@require_http_methods(['GET', 'POST'])
@login_required
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

    if page_size == 50:
        page_size = 50

    folder = None
    folder_slug = None
    search_term = None
    files=list()
    folders=list()

    if request.method == 'POST':
        # search for files and folders
        search_term = request.POST.get('search_term')

        if search_term:
            files = FileRecord.objects.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term),
                user=request.user,
                is_deleted=False
            )
            
            folders = FolderRecord.objects.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term),
                user=request.user,
                is_deleted=False
            )

    else:

        folder_slug = request.GET.get('dossier')
                    
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
            )
            
            files = [file for file in files if file.is_shared]

            # shared folders
            folders = FolderRecord.objects.filter(
                is_deleted=False,
                user=request.user,
            )
            
            folders = [folder for folder in folders if folder.is_shared]
            
        elif folder_slug == 'partages-avec-moi':
            # files shared with me
            logger.info(f'fetching {folder_slug}...')

            shared_files = ShareRecord.objects.filter(
                recipient=request.user,
                file__isnull=False,             
                file__is_deleted=False,    
                is_deleted=False,
                expires_at__gt=timezone.now()
            ).exclude(file__user=request.user)
            
            shared_folder = ShareRecord.objects.filter(
                recipient=request.user,
                folder__isnull=False,
                folder__is_deleted=False,    
                is_deleted=False,
                expires_at__gt=timezone.now()
            ).exclude(file__user=request.user)

            files = [share.file for share in shared_files if share.file.is_shared]
            folders = [share.folder for share in shared_folder if share.folder.is_shared]

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

            files = folder.files.all().filter(is_deleted=False)
            
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
        'recent_folders': folders[:10],
        'search_term': search_term
    })

@require_http_methods(['GET'])
@login_required
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

        parent_slug = request.GET.get('dossier')

        if parent_slug:
            url = reverse('my-box')
            return redirect(f"{url}?dossier={parent_slug}")
        
        return redirect('my-box')

    return render(request, 'drive/file/file-details.html', {
        'file': file
    })

@require_http_methods(['POST'])
@login_required
def rename_file_info_view(request, slug):
    """
    Rename file name
    """
    
    file_record = FileRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        user=request.user
    ).first()

    # print(slug, len(slug))
    # print(request.user)
    # print(file_record)
    
    print(repr(slug), len(slug))
    
    if not file_record:
        
        print(FileRecord.objects.filter(slug=slug))  # filter only by slug
        print(FileRecord.objects.filter(slug=slug, user=request.user))  # slug + user
        print(FileRecord.objects.filter(slug=slug, is_deleted=False)) 

        messages.warning(request, 'Fichier introuvable')

        return redirect('my-box')

    new_name = request.POST.get('name')

    if not is_safe_filename(new_name):
        messages.warning(request, 'Nom de fichier invalide')
        return redirect('file-details', file_record.slug)

    name, _ = os.path.splitext(new_name)
    description = request.POST.get('description', '')

    _, old_ext = os.path.splitext(file_record.name)

    file_record.name = f"{name}{old_ext}"
    file_record.description = description
    
    file_record.save()

    file_record.refresh_from_db()

    messages.success(request, 'Sauvegardé')

    return redirect('file-details', file_record.slug)

@require_http_methods(['POST'])
@login_required
def rename_folder_view(request, slug):
    """
    Rename folder
    """
    
    folder = FolderRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        user=request.user
    ).first()
    
    parent_slug = request.GET.get('dossier')

    if not folder:

        messages.warning(request, 'Dossier introuvable')

        if parent_slug:
            url = reverse('my-box')
            return redirect(f"{url}?dossier={parent_slug}")
        
        return redirect('my-box')
    
    name = request.POST.get('name')

    if not is_safe_foldername(name):

        messages.warning(request, 'Nom de dossier invalide')

        url = reverse('my-box')
        return redirect(f"{url}?dossier={folder.slug}")
        
    description = request.POST.get('description', '')
    
    folder.name = name
    folder.description = description

    folder.save()
    folder.refresh_from_db()

    messages.success(request, 'Sauvegardé')

    url = reverse('my-box')
    return redirect(f"{url}?dossier={folder.slug}")
    
@require_http_methods(['GET'])
@xframe_options_exempt
@login_required
def view_file_content_view(request, slug):
    """
    View file content
    """
    
    file_record = FileRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        user=request.user
    ).first()
    
    if not file_record or not file_record.file:

        parent_slug = request.GET.get('dossier')

        if parent_slug:
            url = reverse('my-box')
            return redirect(f"{url}?dossier={parent_slug}")
        
        return redirect('my-box')

    # Determine content type
    mime_type, _ = mimetypes.guess_type(file_record.name)
    if not mime_type:
        mime_type = 'application/octet-stream'

    response = FileResponse(file_record.file.open('rb'), content_type=mime_type)
    
    # update metadata
    file_record.last_accessed_at = timezone.now()
    file_record.save()

    # Set inline disposition
    response['Content-Disposition'] = f'inline; filename="{file_record.name}"'
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response

@require_http_methods(['GET'])
@login_required
def download_file_view(request, slug):
    """
    Download file
    """
    
    file_record = FileRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        user=request.user
    ).first()
    
    if not file_record or not file_record.file:
        messages.warning(request, 'Fichier introuvable')

        parent_slug = request.GET.get('dossier')

        if parent_slug:
            url = reverse('my-box')
            return redirect(f"{url}?dossier={parent_slug}")
        
        return redirect('my-box')
    
    # update meta
    file_record.last_accessed_at = timezone.now()
    file_record.save()

    return FileResponse(file_record.file.open('rb'), as_attachment=True, filename=file_record.name)

@require_http_methods(['GET'])
@login_required
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

        parent_slug = request.GET.get('dossier')

        if parent_slug:
            url = reverse('my-box')
            return redirect(f"{url}?dossier={parent_slug}")
        
        return redirect('my-box')
    
    # soft delete non-empty folders
    delete_folder_and_contents(folder)
    
    messages.success(request, 'Dossier supprimeé')

    parent = folder.parent

    if parent:
        url = reverse('my-box')
        return redirect(f"{url}?dossier={parent.slug}")

    return redirect('my-box')

@require_http_methods(['GET'])
@login_required
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

        parent_slug = request.GET.get('dossier')

        if parent_slug:
            url = reverse('my-box')
            return redirect(f"{url}?dossier={parent_slug}")

        return redirect('my-box')
    
    file.is_deleted = True
    file.deleted_at = timezone.now()
    file.shared_at = None
    file.save()
    
    messages.success(request, 'Fichier supprimé')
    
    parent = file.folder

    if parent:
        url = reverse('my-box')
        return redirect(f"{url}?dossier={parent.slug}")

    return redirect('my-box')

@require_http_methods(['GET'])
@login_required
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

        parent_slug = request.GET.get('dossier')

        if parent_slug:
            url = reverse('my-box')
            return redirect(f"{url}?dossier={parent_slug}")
        
        return redirect('my-box')
    
    if request.method == 'POST':

        folder.shared_at = timezone.now()
        folder.save(update_fields=['shared_at'])

        messages.success(request, 'Dossier partagé')

        return redirect('share-folder', slug=slug)
        
    folders = folder.subfolders.all()
    files = folder.files.all()
        
    items = list(folders) + list(files)
        
    paginator = Paginator(items, 20) 
    page_obj = paginator.get_page(1)
    
    contacts = ContactDetails.objects.filter(
        is_deleted=False,
        user=request.user
    )[:1500]

    contact_groups = ContactGroup.objects.filter(
        is_deleted=False,
        user=request.user
    )

    return render(request, 'drive/folder/share-folder.html', {
        'folder': folder,
        'items': page_obj,
        'contacts': contacts,
        'contact_groups': contact_groups
    })

@require_http_methods(['GET'])
@login_required
def download_folder_view(request, slug):
    """
    Download folder
    """
    
    folder = FolderRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        user=request.user
    ).first()
    
    parent_slug = request.GET.get('dossier')

    if not folder:
        messages.warning(request, 'Dossier introuvable')

        if parent_slug:
            url = reverse('my-box')
            return redirect(f"{url}?dossier={parent_slug}")
        
        return redirect('my-box')
    
    if folder.is_over_30mb():
        # check folder size before download 
        # if it is too large, create background 
        # and redirect user to waiting page
        
        messages.warning(request, 'Dossier trop large')

        if parent_slug:
            url = reverse('my-box')
            return redirect(f"{url}?dossier={parent_slug}")

        return redirect('my-box')
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        add_folder_to_zip(zip_file, folder, base_path=folder.name)

    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{folder.name}.zip"'
    return response

@require_http_methods(['GET', 'POST'])
@login_required
def share_file_view(request, slug):
    """
    Share file
    """
    
    file = FileRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        user=request.user
    ).first()

    if not file:
        messages.warning(request, 'Fichier introuvable')

        parent_slug = request.GET.get('dossier')

        if parent_slug:
            url = reverse('my-box')
            return redirect(f"{url}?dossier={parent_slug}")

        return redirect('my-box')
    
    if request.method == 'POST':

        file.shared_at = timezone.now()
        file.save(update_fields=['shared_at'])

        messages.success(request, 'Fichier partagé')

        return redirect('share-file', slug=slug)
        
    contacts = ContactDetails.objects.filter(
        is_deleted=False,
        user=request.user
    )[:1500]

    contact_groups = ContactGroup.objects.filter(
        is_deleted=False,
        user=request.user
    )
        
    return render(request, 'drive/file/share-file.html', {
        'file': file,
        'contacts': contacts,
        'contact_groups': contact_groups
    })

@require_http_methods(['GET'])
@login_required
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
    
    elif not slug_type and not folder_slug:
        return redirect('file-details', slug)
    
    elif file and file.folder:
        return redirect(f"{url}?dossier={file.folder.slug}")
    
    return redirect('my-box')

@require_http_methods(['POST'])
@login_required
def create_folder_view(request):
    """
    Create a new folder
    """
    
    parent_slug = request.GET.get('dossier')
    folder = None
    
    if parent_slug:
        folder = FolderRecord.objects.filter(
            user=request.user,
            is_deleted=False,
            slug=parent_slug
        ).first()
        
        if not folder:
            messages.warning(request, 'Dossier introuvable')
            return redirect('my-box')
        
        # check for folder depth
        
    name = request.POST.get('name')
    
    if not name:
        messages.warning(request, 'Erreur')

        if parent_slug:
            url = reverse('my-box')
            return redirect(f"{url}?dossier={parent_slug}")

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
@login_required
def upload_files_view(request):
    """
    Upload files
    """
    
    parent_slug = request.GET.get('dossier')
    folder = None
    
    if parent_slug:
        folder = FolderRecord.objects.filter(
            slug=parent_slug,
            user=request.user,
            is_deleted=False,
        ).first()
        
        if not folder:
            messages.warning(request, 'Dossier introuvalbe')
            return redirect('my-box')
    
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

    return_url = 'my-box'

    if parent_slug:
        return_url = reverse('my-box')
        return_url =f"{return_url}?dossier={parent_slug}"

    if last_hour_count + len(files) > MAX_FILES_COUNT_PER_HOUR:
        # too many upload per hour
        messages.warning(request, f"Limite atteinte : {MAX_FILES_COUNT_PER_HOUR} fichiers maximum par heure")
        return redirect(return_url)
    
    if last_day_count + len(files) > MAX_FILES_COUNT_PER_DAY:
        # too many upload per day
        messages.warning(request, F"Limite atteinte : {MAX_FILES_COUNT_PER_DAY} fichiers maximum par heure")
        return redirect(return_url)
    
    # Count files
    num_files = len(files)

    # Total size in bytes
    total_size = sum(f.size for f in files)
    
    if num_files > MAX_FILES_COUNT_PER_REQUEST:
        # Too many files
        messages.warning(request, f"Trop de fichiers. Le maximum est de {MAX_FILES_COUNT_PER_REQUEST}")
        return redirect(return_url)

    if total_size > MAX_TOTAL_UPLOAD_SIZE:
        # request too large
        messages.warning(request, "Téléversement trop volumineux")
        return redirect(return_url)
    
    for file in files:
        # check file extensions

        if not is_extension_safe(file):
            messages.warning(request, "Fichier incompatibles detecté")
            logger.warning(file.name)
            return redirect(return_url)
        
        if not is_safe_filename(file.name):
            messages.warning(request, "Nom de fichier invalide detecté")
            logger.warning(file.name)
            return redirect(return_url)

        if file.size > ALLOWED_FILE_SIZE:
            messages.warning(request, "Fichier trop large detecté")
            logger.warning(file.name)
            return redirect(return_url)

    for uploaded_file in files:
        FileRecord.objects.create(
            user=user,
            file=uploaded_file,
            folder=folder,
            name=uploaded_file.name
        )

    messages.success(request, 'Fichers sauvegardés')
    return redirect(return_url)

@require_http_methods(['GET'])
@login_required
def trash_bin_view(request):
    """
    View deleted files
    """
    
    files = FileRecord.objects.filter(
        user=request.user,
        is_deleted=True,
        is_archived=False,
    ).order_by('-deleted_at')
    
    return render(request, 'drive/trash-bin.html', {
        'files': files[:100]
    })
    
@require_http_methods(['POST'])
@login_required
def restore_deleted_file_view(request, slug):
    """
    Restore deleted file
    """
    
    file = FileRecord.objects.filter(
        slug=slug,
        user=request.user,
        is_deleted=True,
        is_archived=False,
    ).first()
    
    if not file:
        messages.warning(request, 'Fichier introuvable')
        return redirect('my-trash')
    
    # restore file
    file.is_deleted = False
    file.deleted_at = None
    
    file.save()
    
    # restore all parent folders
    folder = file.folder
    while folder:
        if folder.is_deleted:
            folder.is_deleted = False
            folder.deleted_at = None
            folder.save()
        folder = folder.parent
    
    messages.success(request, 'Fichier restoré')

    return redirect('my-trash')

@require_http_methods(['POST'])
@login_required
def archive_file_view(request, slug):
    """
    Archive deleted file - permanent logical deletion
    """
    
    file = FileRecord.objects.filter(
        slug=slug,
        user=request.user,
        is_deleted=True,
        is_archived=False,
    ).first()
    
    if not file:
        messages.warning(request, 'Fichier introuvable')
        return redirect('my-trash')
    
    file.is_archived = True
    file.archived_at = timezone.now()
    
    file.save()
    
    messages.success(request, 'Fichier archivé')

    return redirect('my-trash')

@require_http_methods(['POST'])
@login_required
def create_contact_view(request):
    """
    Create new contact record
    """
    
    file_slug = request.GET.get('file')
    folder_slug = request.GET.get('folder')
    group_id = request.GET.get('group', '')
    groups_ids = [int(pk) for pk in request.POST.getlist('groups', []) if pk.strip()]

    file = None
    folder = None
    group = None
    groups = list()

    if file_slug:
        file = FileRecord.objects.filter(
            slug=file_slug,
            is_deleted=False,
            user=request.user
        ).first()

    elif folder_slug:
        folder = FolderRecord.objects.filter(
            slug=file_slug,
            is_deleted=False,
            user=request.user
        ).first()

    if group_id:
        group = ContactGroup.objects.filter(
            id=group_id,
            is_deleted=False,
            user=request.user
        ).first()

        if not group:
            messages.warning(request, 'Groupe introuvable')
            return redirect('my-contacts')
    
    if groups_ids:
        groups = ContactGroup.objects.filter(
            id__in=groups_ids,
            is_deleted=False,
            user=request.user
        )

    first_name = request.POST.get('first_name')
    last_name = request.POST.get('last_name')
    email = request.POST.get('email')
    
    if not (first_name and last_name and email):
        messages.warning(request, 'Données invalides')
        return redirect('my-box')
    
    contact = ContactDetails.objects.create(
        first_name=first_name,
        last_name=last_name,
        user=request.user,
        email=email,
    )

    if groups:
        contact.groups.set(groups)
    
    messages.success(request, 'Contact enregistré')
    
    # find recipient account
    recipient = User.objects.filter(email=email).first()
    
    if file:
        ShareRecord.objects.create(
            file=file,
            expires_at=file.share_expires_at,
            recipient=recipient,
            contact=contact
        )

        return redirect('share-file', file.slug)
    
    elif folder:
        ShareRecord.objects.create(
            folder=folder,
            expires_at=folder.share_expires_at,
            recipient=recipient,
            contact=contact
        )

        if not folder.is_shared:
            folder.shared_at = timezone.now()
            folder.save()

        return redirect('share-folder', folder.slug)
    
    elif group and group.id in groups_ids:
        url = reverse('my-contacts')
        return redirect(f'{url}?group={group.pk}')

    else:
        return redirect('my-contacts')
    
@require_http_methods(['POST'])
@login_required
def edit_contact_view(request, contact_id):
    """
    Edit contact details
    """
    
    contact = ContactDetails.objects.filter(
        id=contact_id,
        is_deleted=False,
        user=request.user
    ).first()

    if not contact:
        messages.warning(request, 'Contact introuvable')
        return redirect('my-contacts')

    group_id = request.GET.get('group', '')
    groups_ids = [int(pk) for pk in request.POST.getlist('groups', []) if pk.strip()]

    group = None
    groups = list()

    if group_id:
        group = ContactGroup.objects.filter(
            id=group_id,
            is_deleted=False,
            user=request.user
        ).first()

        if not group:
            messages.warning(request, 'Groupe introuvable')
            return redirect('my-contacts')

    first_name = request.POST.get('first_name')
    last_name = request.POST.get('last_name')
    email = request.POST.get('email')
    groups_ids = [int(pk) for pk in request.POST.getlist('groups', []) if pk.strip()]

    if not (first_name and last_name and email):
        messages.warning(request, 'Données invalides')
        return redirect('my-box')
    
    if groups_ids:
        groups = ContactGroup.objects.filter(
            id__in=groups_ids,
            is_deleted=False,
            user=request.user
        )
    
    contact.first_name = first_name
    contact.last_name = last_name
    contact.email = email
    contact.save()

    contact.groups.set(groups)
    
    messages.success(request, 'Contact mis à jour')
    
    if group and group.id in groups_ids:
        url = reverse('my-contacts')
        return redirect(f'{url}?group={group.pk}')

    else:
        return redirect('my-contacts')
    
@require_http_methods(['POST'])
@login_required
def delete_contact_view(request, contact_id):
    """
    Delete contact
    """
    
    contact = ContactDetails.objects.filter(
        id=contact_id,
        is_deleted=False,
        user=request.user
    ).first()

    if not contact:
        messages.warning(request, 'Contact introuvable')
        return redirect('my-contacts')

    group_id = request.GET.get('group', '')

    group = None

    if group_id:
        group = ContactGroup.objects.filter(
            id=group_id,
            is_deleted=False,
            user=request.user
        ).first()

        if not group:
            messages.warning(request, 'Groupe introuvable')
            return redirect('my-contacts')

    contact.is_deleted = True
    contact.deleted_at = timezone.now()
    contact.save()

    # exit all groups
    contact.groups.clear()
    
    messages.success(request, 'Contact supprimé')
    
    if group:
        url = reverse('my-contacts')
        return redirect(f'{url}?group={group.pk}')

    else:
        return redirect('my-contacts')

@require_http_methods(['GET'])
@login_required
def add_contact_to_shared_item_view(request, contact_id):
    """
    Add contact to file or folder
    """
    
    contact = ContactDetails.objects.filter(
        id=contact_id,
        is_deleted=False,
        user=request.user
    ).first()
    
    if not contact:
        messages.warning(request, 'Contact introuvable')
        return redirect('my-box')
    
    file_slug = request.GET.get('file')
    folder_slug = request.GET.get('folder')

    file = None
    folder = None

    if file_slug:        
        file = FileRecord.objects.filter(
            slug=file_slug,
            is_deleted=False,
            user=request.user
        ).first()

    elif folder_slug:
        folder = FolderRecord.objects.filter(
            slug=folder_slug,
            is_deleted=False,
            user=request.user
        ).first()
        
    recipient = User.objects.filter(email=contact.email).first()

    if file:
        
        all_access = file.get_unique_share_records_with_access()
        
        existing_record = all_access.filter(
            contact=contact,
        )
        
        if existing_record:
            messages.success(request, 'Contact déjà ajouté')
            return redirect('share-file', file.slug)
        
        if len(file.get_unique_share_records_with_access()) > 99:
            messages.warning(request, 'Partage limité à 100 personnes')
            return redirect('share-file', file.slug)
        
        ShareRecord.objects.create(
            file=file,
            expires_at=file.share_expires_at,
            recipient=recipient,
            contact=contact
        )
        
        if not file.is_shared:
            file.shared_at = timezone.now()
            file.save()

        messages.success(request, 'Contact ajouté')
            
        return redirect('share-file', file.slug)
    
    elif folder:
        
        all_access = folder.get_unique_share_records_with_access()
        
        existing_record = all_access.filter(
            contact=contact,
        )
        
        if existing_record:
            messages.success(request, 'Contact déjà ajouté')
            return redirect('share-folder', folder.slug)
        
        if len(folder.get_unique_share_records_with_access()) > 99:
            messages.warning(request, 'Partage limité à 100 personnes')
            return redirect('share-folder', folder.slug)
        
        ShareRecord.objects.create(
            folder=folder,
            expires_at=folder.share_expires_at,
            recipient=recipient,
            contact=contact
        )
        
        if not folder.is_shared:
            folder.shared_at = timezone.now()
            folder.save()

        messages.success(request, 'Contact ajouté')

        return redirect('share-folder', folder.slug)
    
    else:
        messages.warning(request, 'Fichier ou dossier introuvable')
        return redirect('my-box')
    
 
@require_http_methods(['GET'])
@login_required
def remove_contact_from_shared_item_view(request, share_id):
    """
    Remove contact from file or folder
    """
    
    share = ShareRecord.objects.filter(
        id=share_id,
        is_deleted=False,
        contact__is_deleted=False,
        contact__user=request.user,
    ).first()
    
    if not share:
        messages.warning(request, 'Partage introuvable')
        return redirect('my-box')
    
    share.is_deleted = True
    share.deleted_at = timezone.now()
    share.save()
    
    if share.file:
        all_access = share.file.get_share_records_with_access()
        
        other_user_access = all_access.filter(
            Q(contact=share.contact) | Q(contact__email=share.contact.email)
        )
        
        if other_user_access:
            logger.info(f'{len(other_user_access)} other access of the same contact found')
            logger.info('removing other shares...')
            
            for record in other_user_access:
                record.is_deleted = True
                record.deleted_at = timezone.now()
                record.save()
            
        messages.success(request, 'Contact enlevé')
        return redirect('share-file', share.file.slug)
    
    else:
        
        all_access = share.folder.get_share_records_with_access()
        
        other_user_access = all_access.filter(
            Q(contact=share.contact) | Q(contact__email=share.contact.email)
        )
        
        if other_user_access:
            logger.info(f'{len(other_user_access)} other access of the same contact found')
            logger.info('removing other shares...')
            
            for record in other_user_access:
                record.is_deleted = True
                record.deleted_at = timezone.now()
                record.save()
        
        messages.success(request, 'Contact enlevé')
        return redirect('share-folder', share.folder.slug)
    
@require_http_methods(['GET', 'POST'])
@login_required
def all_contacts_view(request):
    
    page_size = request.GET.get('page_size', '50')
    if is_valid_int(page_size):
        page_size = int(page_size)
    else:
        page_size = 50
    
    page = request.GET.get('page', '1')
    if is_valid_int(page):
        page = int(page) 
    else:
        page = 1

    if page_size > 50:
        page_size = 50
        
    group_id = None
    group = None
    search_term = None
    contacts = list()

    if request.method == 'POST':

        search_term = request.POST.get('search_term')

        if search_term:
            contacts = ContactDetails.objects.filter(
                Q(first_name__icontains=search_term) |
                Q(last_name__icontains=search_term) |
                Q(email__icontains=search_term),
                user=request.user,
                is_deleted=False
            )
    else:

        group_id = request.GET.get('group')
        
        if group_id:
            group = ContactGroup.objects.filter(
                is_deleted=False,
                user=request.user,
                id=group_id
            ).first()
            
            if not group:
                messages.warning(request, 'Groupe introuvable')
                return redirect('my-contacts')
            
            contacts = group.contacts.all().filter(
                is_deleted=False
            )
            
        else:
            contacts = ContactDetails.objects.filter(
                is_deleted=False,
                user=request.user
            )
    
    contact_groups = ContactGroup.objects.filter(
        is_deleted=False,
        user=request.user
    )
    
    paginator = Paginator(contacts, page_size) 
    page_obj = paginator.get_page(page)
    
    return render(request, 'contacts/contacts.html', {
        'contacts': page_obj,
        'contact_groups': contact_groups,
        'group': group,
        'search_term': search_term
    })


@require_http_methods(['POST'])
@login_required
def create_contact_group_view(request):
    """
    Create new contact group
    """
    
    name = request.POST.get('name')
    description = request.POST.get('description')
    
    if not name:
        messages.warning(request, 'Données invalides')
        return redirect('my-contacts')
    
    group = ContactGroup.objects.create(
        name=name,
        description=description,
        user=request.user
    )
    
    messages.success(request, 'Groupe enregistré')

    url = reverse('my-contacts')

    return redirect(f'{url}?group={group.pk}')

@require_http_methods(['GET'])
@login_required
def contact_group_details_view(request, group_id):
    return redirect('my-contacts')

@require_http_methods(['POST'])
@login_required
def delete_contact_group_view(request, group_id):

    group = ContactGroup.objects.filter(
        id=group_id,
        is_deleted=False,
        user=request.user
    ).first()
        
    if not group:
        messages.warning(request, 'Groupe introuvable')
        return redirect('my-contacts')
    
    group.is_deleted = True
    group.deleted_at = timezone.now()
    group.save()

    # remove all contacts from the group
    group.contacts.clear()
    
    messages.success(request, 'Groupe supprimé')

    return redirect('my-contacts')

@require_http_methods(['POST'])
@login_required
def edit_contact_group_view(request, group_id):

    group = ContactGroup.objects.filter(
        id=group_id,
        is_deleted=False,
        user=request.user
    ).first()
        
    if not group:
        messages.warning(request, 'Groupe introuvable')
        return redirect('my-contacts')
    
    name = request.POST.get('name')
    description = request.POST.get('description')

    if not name:
        messages.warning(request, 'Données invalides')
        return redirect('my-contacts')
    
    group.name = name
    group.description = description
    group.save()

    messages.success(request, 'Groupe enregistré')

    url = reverse('my-contacts')

    return redirect(f'{url}?group={group.pk}')

@require_http_methods(['POST'])
@login_required
def add_contact_group_to_item_view(request):
    
    file_slug = request.GET.get('file')
    folder_slug = request.GET.get('folder')
    groups_ids = [int(pk) for pk in request.POST.getlist('groups', []) if pk.strip()]

    file = None
    folder = None
    groups = list()

    if file_slug:
        file = FileRecord.objects.filter(
            slug=file_slug,
            is_deleted=False,
            user=request.user
        ).first()

    elif folder_slug:
        folder = FolderRecord.objects.filter(
            slug=file_slug,
            is_deleted=False,
            user=request.user
        ).first()

    if groups_ids:
        groups = ContactGroup.objects.filter(
            id__in=groups_ids,
            is_deleted=False,
            user=request.user
        )
        
    contacts = ContactDetails.objects.filter(groups__in=groups).distinct()
    
    if file:
        
        if len(file.get_share_records_with_access()) + contacts.count() > 99:
            messages.warning(request, 'Partage limité à 100 personnes')
            return redirect('share-file', file.slug)
        
        for contact in contacts:
            share, created = ShareRecord.objects.get_or_create(
                contact=contact,
                file=file,
                defaults={'is_deleted': False}
            )
            
            if not created and share.is_deleted:
                share.is_deleted = False
                share.deleted_at = None
                share.save()
        
        messages.success(request, 'Contact ajouté')
            
        return redirect('share-file', file.slug)
    
    elif folder:
        
        if len(folder.get_share_records_with_access()) + contacts.count() > 99:
            messages.warning(request, 'Partage limité à 100 personnes')
            return redirect('share-file', file.slug)
        
        for contact in contacts:
            share, created = ShareRecord.objects.get_or_create(
                contact=contact,
                folder=folder,
                defaults={'is_deleted': False}
            )
            
            if not created and share.is_deleted:
                share.is_deleted = False
                share.deleted_at = None
                share.save()
            
            messages.success(request, 'Contact ajouté')

        return redirect('share-folder', folder.slug)
    
    
    messages.success(request, 'Groupe supprimé')

    return redirect('my-contacts')
