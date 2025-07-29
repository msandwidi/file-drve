from django.shortcuts import render

# Create your views here.
def my_drive_view(request):
    return render(request, 'drive/my-drive.html')