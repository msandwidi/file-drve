from drive.models import (
    ShareRecord, 
)
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import FileResponse, HttpResponse
from django.contrib import messages
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
        slug=slug,
        is_deleted=False,
        #recipient=request.user,
        file__isnull=False,
        file__is_deleted=False,
        contact__is_deleted=False,
    ).first()
    
    if not share:
        messages.warning(request, 'Fichier introuvable')
        return redirect('my-box')

    return render(request, 'shared/file/file-details.html', {
        'share': share,
    })

@require_http_methods(['GET'])
@login_required
def shared_folder_details(request, slug):
    """
    Get share folder details
    """
    
    share = ShareRecord.objects.filter(
        slug=slug,
        is_deleted=False,
        #recipient=request.user,
        folder__is_deleted=False,
        contact__is_deleted=False,
    ).first()

    if not share:
        messages.warning(request, 'Dossier introuvable')
        return redirect('my-box')

    return render(request, 'shared/folder/folder-details.html', {
        'share': share,
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
    file = None
    
    return redirect('file-details', file.slug)
