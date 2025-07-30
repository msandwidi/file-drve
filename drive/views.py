from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect
from .models import FileRecord, FolderRecord
from django.core.paginator import Paginator
from django.contrib import messages
from core.utils import is_valid_int
from django.urls import reverse

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
        
    folder_id = request.GET.get('dossier')
    folder = None
    
    if is_valid_int(folder_id):
        folder = FolderRecord.objects.filter(
            id=folder_id,
            user=request.user,
            is_deleted=False,
        ).first()
    
    if folder_id == 'fichiers-recents':
        files = FileRecord.objects.filter(
            user=request.user,
            is_deleted=False,
        ).order_by('-last_accessed_at')
        
    elif folder:
        # folder files
        files = folder.files.all()
        
        folders = folder.subfolders.all()
        
    else:
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
        
    paginator = Paginator(files, page_size) 
    page_obj = paginator.get_page(page)
    
    return render(request, 'drive/my-drive.html', {
        'files': page_obj,
        'folders': folders,
        'folder': folder,
    })

def file_details_view(request, file_id):
    """
    Get file details
    """
    
    file = FileRecord.objects.filter(
        id=file_id,
        is_deleted=False,
        user=request.user
    ).first()
    
    if not file:
        return redirect('my-box')

    return render(request, 'file/file-details.html', {
        'file': file
    })

@require_http_methods(['POST'])
def create_folder_view(request):
    """
    Create a new folder
    """
    
    folder_id = request.GET.get('dossier')
    folder = None
    
    if folder_id:
        folder = FolderRecord.objects.filter(
            user=request.user,
            is_deleted=False,
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
    return redirect(f"{url}?dossier-{new_folder.id}")

def trash_bin_view(request):
    return render(request, 'drive/trash-bin.html')