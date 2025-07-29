from django.shortcuts import  render, redirect, HttpResponse
from django.views.decorators.http import require_http_methods
from .forms import ContactForm

# Create your views here.

@require_http_methods(['GET', 'POST'])
def home(request):
    """
    Home page
    """
    
    if request.method == 'GET' and request.user.is_authenticated:
        return redirect('my-box')  

    return render(request, 'home/home.html')

@require_http_methods(['GET', 'POST'])
def contact_us_view(request):
    """
    Handle contact us form
    """
    
    if request.method == 'POST':
        form = ContactForm(request.POST)
        
        if form.is_valid():
            form.save()
            
            return render(request, 'contact/thank-you.html')
    else:
        form = ContactForm()

    return render(request, 'contact/contact-us.html', {'form': form})

@require_http_methods(['GET'])
def privacy_view(request):
    return render(request, 'terms/privacy.html')

@require_http_methods(['GET'])
def terms_view(request):
    return render(request, 'terms/tos.html')

@require_http_methods(['GET'])
def robots_txt_view(request):
    content = "User-agent: *\nDisallow: /"
    return HttpResponse(content, content_type="text/plain")

