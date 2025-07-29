from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('robots.txt', views.robots_txt_view, name='robots.txt'),
    path('condition-dutilisation', views.terms_view, name='tos'),
    path('contactez-nous', views.contact_us_view, name='contact-us'),
    path('politique-de-confidentialite', views.privacy_view, name='privacy'),
]