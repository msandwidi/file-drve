from django.shortcuts import render, redirect
from core.utils import is_valid_int
from django.core.paginator import Paginator
from .models import FileRecord, FolderRecord

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
    
    if folder_id:
        folder = FolderRecord.objects.filter(
            user=request.user,
            is_deleted=False,
        ).first()
        
    if folder:
        files = FileRecord.objects.filter(
            user=request.user,
            is_deleted=False,
            folder=folder
        )
        
    else:
        files = FileRecord.objects.filter(
            user=request.user,
            is_deleted=False,
        )

    # my folders
    folders = FolderRecord.objects.filter()
        
    paginator = Paginator(files, page_size) 
    page_obj = paginator.get_page(page)
    
    return render(request, 'drive/my-drive.html', {
        'files': page_obj,
        'folders': folders
    })


def file_details_view(request, file_id):
    """
    Get file details
    """
    
    file = FileRecord.objects.filter(
        id=file_id,
        is_deleted=False
    ).first()
    
    if not file:
        return redirect('my-box')

    return render(request, 'file/file-details.html', {
        'file': file
    })

def create_folder_view(request):
    """
    Create a new folder
    """
    return render(request, 'drive/new-folder.html')

def trash_bin_view(request):
    return render(request, 'drive/trash-bin.html')