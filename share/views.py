from drive.models import (
    ShareRecord,
    FileRecord,
    FolderRecord
)
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.contrib import messages
from core.utils import is_valid_int
from django.utils import timezone
from django.urls import reverse
from django.db.models import Q
import logging
import mimetypes
import zipfile
import os
import io

logger = logging.getLogger(__name__)

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

# Create your views here
@require_http_methods(['GET'])
@login_required
def shared_file_details(request, slug):
    """
    Get share file details
    """
    
    share = ShareRecord.objects.filter(
        is_deleted=False,
        #recipient=request.user,
        file__isnull=False,
        file__is_deleted=False,
        contact__is_deleted=False,
    ).filter(
        Q(slug=slug) |
        Q(file__slug=slug) 
    ).first()

    if not share:
        logger.warning('file share not found')
        messages.warning(request, 'Fichier introuvable')
        return redirect('my-box')
    
    return render(request, 'shared/file/file-details.html', {'share': share})

@require_http_methods(['GET'])
@login_required
def shared_folder_details(request, slug):
    """
    Get share folder details
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

    if page_size > 50:
        page_size = 50
    
    share = ShareRecord.objects.filter(
        is_deleted=False,
        #recipient=request.user,
        folder__isnull=False,
        folder__is_deleted=False,
        contact__is_deleted=False,
    ).filter(
        Q(slug=slug) |
        Q(folder__slug=slug) 
    ) .first()

    if not share:
        messages.warning(request, 'Dossier introuvable')
        return redirect('my-box')
    
    logger.info('Share found')
    
    folder_slug = request.GET.get('folder')
    file_slug = request.GET.get('file')
    folder = None
    file = None
    folder_parents=list()
    
    if folder_slug and share.folder.contains_folder_with_slug(folder_slug):
        logger.info('finding subfolder of shared folder...')
        folder = FolderRecord.objects.filter(
            is_deleted = False,
            slug = folder_slug    
        ).first()
        
        if not folder:
            logger.warning('unable to find selected folder ' + folder_slug)
            return redirect('shared-folder-details', slug)
        
        folder_parents = folder.get_parents_until_slug(slug)
        
    if file_slug and share.folder.contains_file_with_slug(file_slug):
        logger.info('finding file of shared folder...')
        file = FileRecord.objects.filter(
            is_deleted = False,
            slug = file_slug    
        ).first()
        
        if not file:
            logger.warning('unable to find selected file ' + file_slug)
            return redirect('shared-folder-details', slug)
        
    folders = list()
    files = list()
    
    if not folder:
        logger.info('Getting content of shared folder...')
        folders = share.folder.subfolders.all().filter(is_deleted=False)
        files = share.folder.files.all().filter(is_deleted=False)
        folder = share.folder
        
    else:   
        logger.info('Getting content of selected folder...')
        folders = folder.subfolders.all().filter(is_deleted=False)
        files = folder.files.all().filter(is_deleted=False)
        
    items = list(folders) + list(files)
        
    paginator = Paginator(items, page_size) 
    page_obj = paginator.get_page(page)

    return render(request, 'shared/folder/folder-details.html', {
        'share': share,
        'items': page_obj,
        'folder': folder,
        'file': file,
        'folder_parents': folder_parents
    })

@require_http_methods(['GET'])
@login_required
def shared_item_details(request, slug):
    """
    Get share item and redirect to appropriate view
    """
    
    share = ShareRecord.objects.filter(
        is_deleted=False,
        contact__is_deleted=False,
        #recipient=request.user,
    ).filter(
        Q(slug=slug) |
        Q(folder__slug=slug, folder__is_deleted=False) |
        Q(file__slug=slug, file__is_deleted=False)
    ).first()

    if not share:
        messages.warning(request, 'Lien introuvable')
        return redirect('my-box')
    
    if share.file:
        logger.warning('redirecting to shared file page...')
        return redirect('shared-file-details', share.slug)
    
    logger.warning('redirecting to shared folder page...')
    return redirect('shared-folder-details', share.slug)

@require_http_methods(['GET'])
@xframe_options_exempt
@login_required
def view_shared_file_content_view(request, slug):
    """
    View file content
    """
    
    share = ShareRecord.objects.filter(
        is_deleted=False,
        contact__is_deleted=False,
        #recipient=request.user,
    ).filter(
        Q(slug=slug) |
        Q(folder__slug=slug, folder__is_deleted=False) |
        Q(file__slug=slug, file__is_deleted=False)
    ).first()
    
    if not share:
        messages.warning(request, 'Lien introuvable')
        return redirect('my-box')
    
    file_slug = request.GET.get('file')
    file = None

    if file_slug and share.folder.contains_file_with_slug(file_slug):
        file = FileRecord.objects.filter(
            slug=file_slug, 
            is_deleted=False,
        ).first()

    if not file:
        messages.warning(request, 'Fichier introuvable')
        return redirect('shared-folder-details', share.slug)
    
    # Determine content type
    mime_type, _ = mimetypes.guess_type(file.name)
    if not mime_type:
        mime_type = 'application/octet-stream'

    response = FileResponse(file.file.open('rb'), content_type=mime_type)
    
    # update metadata
    share.last_accessed_at = timezone.now()
    share.save()

    # Set inline disposition
    response['Content-Disposition'] = f'inline; filename="{file.name}"'
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response

@require_http_methods(['GET'])
@login_required
def download_shared_file_view(request, slug):
    """
    Download shared file
    """
    
    share = ShareRecord.objects.filter(
        is_deleted=False,
        contact__is_deleted=False,
        #recipient=request.user,
    ).filter(
        Q(slug=slug) |
        Q(folder__slug=slug, folder__is_deleted=False) |
        Q(file__slug=slug, file__is_deleted=False)
    ).first()
        
    if not share:
        messages.warning(request, 'Lien introuvable')
        return redirect('my-box')
    
    file_slug = request.GET.get('file')
    file = None

    if share.file:
        file = share.file

    elif file_slug and share.folder and share.folder.contains_file_with_slug(file_slug):
        file = FileRecord.objects.filter(
            slug=file_slug, 
            is_deleted=False,
        ).first()

    if not file or not file.file:
        messages.warning(request, 'Fichier introuvable')
        return redirect('shared-folder-details', share.slug)
    
    share.last_accessed_at = timezone.now()
    share.save()

    return FileResponse(file.file.open('rb'), as_attachment=True, filename=file.name)

@require_http_methods(['GET'])
@login_required
def delete_shared_item_view(request, slug):
    """
    Delete shared file or folder
    """

    share = ShareRecord.objects.filter(
        is_deleted=False,
        contact__is_deleted=False,
        #recipient=request.user,
    ).filter(
        Q(slug=slug) |
        Q(folder__slug=slug, folder__is_deleted=False) |
        Q(file__slug=slug, file__is_deleted=False)
    ).first()
        
    if not share:
        messages.warning(request, 'Lien introuvable')
        return redirect('my-box')
    
    share.is_deleted = True
    share.deleted_at = timezone.now()
    share.expires_at = timezone.now()
    share.save()
    
    messages.success(request, 'Partage supprimé')
    
    return redirect('my-box')

@require_http_methods(['POST'])
@login_required
def copy_shared_file_view(request, slug):
    """
    Copy shared file
    """
    
    share = ShareRecord.objects.filter(
        is_deleted=False,
        contact__is_deleted=False,
        #recipient=request.user,
        file__isnull=False
    ).filter(
        Q(slug=slug) |
        Q(file__slug=slug, file__is_deleted=False)
    ).first()
        
    if not share:
        messages.warning(request, 'Lien introuvable')
        return redirect('my-box')
    
    file_slug = request.GET.get('file')
    file = None

    if share.file:
        file = share.file

    elif file_slug and share.folder and share.folder.contains_file_with_slug(file_slug):
        file = FileRecord.objects.filter(
            slug=file_slug, 
            is_deleted=False,
        ).first()

    if not file or not file.file:
        messages.warning(request, 'Fichier introuvable')
        return redirect('shared-folder-details', share.slug)
    
    # copy file
    new_record = file.copy_file_to_user(request.user)
    
    if new_record:
        messages.success(request, 'Fichier copié')
        return redirect('file-details', new_record.slug)
    
    return redirect('my-box')

@require_http_methods(['POST'])
@login_required
def copy_shared_folder_view(request, slug):
    """
    Copy shared folder
    """
    
    share = ShareRecord.objects.filter(
        is_deleted=False,
        contact__is_deleted=False,
        #recipient=request.user,
        folder__isnull=False
    ).filter(
        Q(slug=slug) |
        Q(folder__slug=slug, folder__is_deleted=False)
    ).first()
        
    if not share:
        messages.warning(request, 'Lien introuvable')
        return redirect('my-box')
    
    folder_slug = request.GET.get('folder')
    folder = None

    if not folder_slug or share.folder.slug == folder_slug:
        folder = share.folder

    elif folder_slug and share.folder.contains_folder_with_slug(folder_slug):
        folder = FolderRecord.objects.filter(
            slug=folder_slug, 
            is_deleted=False,
        ).first()

    if not folder:
        messages.warning(request, 'Dossier introuvable')
        return redirect('shared-folder-details', share.slug)
    
    # copy file
    new_folder = folder.copy_folder_to_user(request.user)

    if new_folder:
        messages.success(request, 'Dossier copié')
        url = reverse('my-box')
        return redirect(f"{url}?dossier={new_folder.slug}")
    
    return redirect('my-box')

@require_http_methods(['GET'])
@login_required
def download_shared_folder_view(request, slug):
    """
    Download shared folder
    """
    
    share = ShareRecord.objects.filter(
        is_deleted=False,
        contact__is_deleted=False,
        #recipient=request.user,
        folder__isnull=False
    ).filter(
        Q(slug=slug) |
        Q(folder__slug=slug, folder__is_deleted=False)
    ).first()
        
    if not share:
        messages.warning(request, 'Lien introuvable')
        return redirect('my-box')
    
    folder_slug = request.GET.get('folder')
    folder = None

    if not folder_slug or share.folder.slug == folder_slug:
        folder = share.folder

    elif folder_slug and share.folder.contains_folder_with_slug(folder_slug):
        folder = FolderRecord.objects.filter(
            slug=folder_slug, 
            is_deleted=False,
        ).first()

    if not folder:
        messages.warning(request, 'Dossier introuvable')
        return redirect('shared-folder-details', share.slug)
    
    if folder.is_over_30mb():
        # check folder size before download 
        # if it is too large, create background 
        # and redirect user to waiting page
        
        messages.warning(request, 'Dossier trop large')
        return redirect('shared-folder-details', slug)
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        add_folder_to_zip(zip_file, folder, base_path=folder.name)

    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{folder.name}.zip"'
    return response