from django.urls import path
from . import views

urlpatterns = [
    path('sso/connexion', views.login_view, name='login'),
    path('sso/inscription', views.signup_view, name='signup'),
    path('sso/connexion/autorise', views.login_authorize_view, name='login-authorize'),
    path('mon-profile', views.my_profile_view, name='my-profile'),
    path('deconnecter', views.logout_view, name='logout'),
]