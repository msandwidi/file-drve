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
from django.http import FileResponse
from django.contrib import messages
from core.utils import is_valid_int
from django.utils import timezone
from django.db.models import Q
import logging
import mimetypes
import zipfile
import os
import io

logger = logging.getLogger(__name__)

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
    
    if folder_slug and share.folder.contains_folder_with_slug(folder_slug):
        logger.info('finding subfolder of shared folder...')
        folder = FolderRecord.objects.filter(
            is_deleted = False,
            slug = folder_slug    
        ).first()
        
        if not folder:
            logger.warning('unable to find selected folder ' + folder_slug)
            return redirect('shared-folder-details', slug)
        
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
        'file': file
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
        slug=slug,
        is_deleted=False,
        contact__is_deleted=False,
        file__isnull=False,
        file__is_deleted=False,    
    ).first()
    
    if not share or not share.file:
        messages.warning(request, 'Lien introuvable')
        return redirect('my-box')
    
    # Determine content type
    mime_type, _ = mimetypes.guess_type(share.file.name)
    if not mime_type:
        mime_type = 'application/octet-stream'

    response = FileResponse(share.file.file.open('rb'), content_type=mime_type)
    
    # update metadata
    share.last_accessed_at = timezone.now()
    share.save()

    # Set inline disposition
    response['Content-Disposition'] = f'inline; filename="{share.file.name}"'
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response

@require_http_methods(['GET'])
@login_required
def download_shared_file_view(request, slug):
    """
    Download shared file
    """
    
    share = ShareRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        contact__is_deleted=False,
        file__isnull=False,
        file__is_deleted=False,    
    ).first()
    
    if not share or not share.file:
        messages.warning(request, 'Lien introuvable')
        return redirect('my-box')
    
    if not share.file or not share.file.file:
        messages.warning(request, 'Fichier introuvable')
        return redirect('my-box')
    
    share.last_accessed_at = timezone.now()
    share.save()

    return FileResponse(share.file.file.open('rb'), as_attachment=True, filename=share.file.name)

@require_http_methods(['GET'])
@login_required
def delete_shared_file_view(request, slug):
    """
    Delete shared file
    """
    
    share = ShareRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        contact__is_deleted=False,
        file__isnull=False,
        file__is_deleted=False,    
    ).first()
    
    if not share or not share.file:
        messages.warning(request, 'Lien introuvable')
        return redirect('my-box')
    
    share.is_deleted = True
    share.deleted_at = timezone.now()
    share.expires_at = timezone.now()
    share.save()
    
    messages.success(request, 'Fichier supprimé')
    
    return redirect('my-box')

@require_http_methods(['GET'])
@login_required
def copy_shared_file_view(request, slug):
    """
    Copy shared file
    """
    
    share = ShareRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        contact__is_deleted=False,
        file__isnull=False,
        file__is_deleted=False,    
    ).first()
    
    if not share or not share.file:
        messages.warning(request, 'Lien introuvable')
        return redirect('my-box')
    
    # copy file
    new_record = share.copy_file_to_user(request.user)
    
    if new_record:
        messages.success(request, 'Fichier copié')
        return redirect('file-details', new_record.slug)
    
    return redirect('my-box')
