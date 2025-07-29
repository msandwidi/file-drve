from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from cryptography.fernet import Fernet
from django.utils import timezone
from .models import UserProfile
from datetime import timedelta
from decouple import config
from . import utils
import logging
import requests
import json

logger = logging.getLogger(__name__)

# Create your views here.

@require_http_methods(['GET'])
def login_view(request):
    """
    Redirect user to SSO login page
    """

    if request.user.is_authenticated:
        return redirect('my-box')
    
    # SSO app config vars
    app_id=config('APP_SSO_PUBLIC_ID', default='')
    sso_login_url=config('APP_SSO_LOGIN_URL', default='')
    
    if not all([app_id.strip(), sso_login_url.strip()]):
        logger.warning('add data not provided in env')
        logger.warning('app_id=%s', app_id)
        logger.warning('sso_login_url=%s', sso_login_url)
        return render(request, 'login/redirect-to-login-error.html')
    
    # redirect to ss
    url = f'{sso_login_url}?app_id={app_id}'
        
    return redirect(url)

@require_http_methods(['GET'])
def login_authorize_view(request):
    """
    Authorize user login session
    """

    if request.user.is_authenticated:
        return redirect('my-box')
    
    # SSO returned session id
    encrypted_session_data = request.GET.get('session', '')
    
    if not encrypted_session_data.strip():
        logger.warning('no session id provided')
        return render(request, 'login/redirect-to-login-error.html')
    
    # SSO app config vars
    app_id = config('APP_SSO_PUBLIC_ID', default='')
    app_secret = config('APP_SSO_SECRET', default='')
    sso_login_url = config('APP_SSO_LOGIN_URL', default='')
    sso_session_validation_url = config('APP_SSO_API_SESSION_VALIDATION_URL', default='')
    
    if not all([
        app_id.strip(), 
        app_secret.strip(),
        sso_login_url.strip(),
        sso_session_validation_url.strip()
    ]):
        logger.warning('missing app config data')
        return render(request, 'login/redirect-to-login-error.html')
    
    decrypted_session_data_str = utils.decrypt_data(encrypted_session_data, app_secret)

    if not decrypted_session_data_str:
        logger.warning('unable to decrypt session payload')
        return render(request, 'login/redirect-to-login-error.html')

    decrypted_session_data_json = json.loads(decrypted_session_data_str)

    # verify user session data with SSO app

    url = f'{sso_session_validation_url}?app_id={app_id}'

    verification_data = {
        'session_id': decrypted_session_data_json['session_id'],
    }
    
    response = requests.post(url, data=verification_data)
    
    if response.ok:
        response = response.text
    else:
        logger.warning('Unexpected SSO response')
        logger.warning('status_code=%s', response.status_code)
        return render(request, 'login/redirect-to-login-error.html')
    
    # all good
    
    # decrypt the profile data
    decrypted_profile_str = utils.decrypt_data(response, app_secret)
    
    if not decrypted_profile_str:
        return render(request, 'login/redirect-to-login-error.html')
    
    profile_json = json.loads(decrypted_profile_str)

    # locate user local account. 
    sso_user_id = profile_json['id']
    
    existing_profile = UserProfile.objects.filter(sso_user_id=sso_user_id).first()

    first_name = profile_json['first_name']
    last_name = profile_json['last_name']
    email = profile_json['email']
    
    if existing_profile:
        # login existing user 

        logger.info('Existing app user profile found. profile id=%s & local user id=%s', existing_profile.id, existing_profile.user.id)

        # update local user
        existing_profile.user.first_name = first_name
        existing_profile.user.last_name = last_name
        existing_profile.user.email = email

        existing_profile.user.save()

        logger.info('Local user account details updated')

        login(request, existing_profile.user)

        logger.info('User has been logged in')

        return redirect('my-box')
    
    else:
        # create mew local profile

        logger.info('Existing local user not found')
        logger.info('Creating new local user for SSO user id=%s', sso_user_id)

        password = utils.random_string()
        username = profile_json['username']
        
        if not User.objects.filter(username=username).exists():
        
            new_local_user = User.objects.create_user(
                username=username, 
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email
            )

            new_user_profile = UserProfile.objects.create(
                sso_user_id=sso_user_id,
                user=new_local_user
            )

            logger.info('New local user created. id=%s', new_local_user.id)
            logger.info('New app profile created. id=%s', new_user_profile.id)
            
            # login new user
            login(request, new_local_user)

            logger.info('New user has been logged in')
            
        else:
            return render(request, 'login/redirect-to-login-error.html')
    
        # redirect to user dashboard
        return redirect('my-box')

@require_http_methods(['GET'])
def signup_view(request):
    """
    Redirect user to SSO signup page
    """
    
    if request.user.is_authenticated:
        return redirect('my-box')
    
    # SSO app config vars
    app_id=config('APP_SSO_PUBLIC_ID', default='')
    sso_signup_url=config('APP_SSO_SIGNUP_URL', default='')
    
    if not all([app_id.strip(),  sso_signup_url.strip()]):
        logger.warning('add data not provided in env')
        logger.warning('app_id=%s', app_id)
        logger.warning('sso_signup_url=%s', sso_signup_url)
        return render(request, 'login/redirect-to-login-error.html')
    
    # redirect to ss
    url = f'{sso_signup_url}?app_id={app_id}'
        
    return redirect(url)

@login_required
def my_profile_view(request):
    """
    User profile
    """

    user = request.user
    
    if request.method == 'POST':
        
        # SSO app config vars
        app_id=config('APP_SSO_PUBLIC_ID', default='')
        app_secret=config('APP_SSO_SECRET', default='')
        sso_account_profile_url=config('APP_SSO_ACCOUNT_PROFILE_URL', default='')
        
        if not all([app_id.strip(), app_secret.strip(), sso_account_profile_url.strip()]):
            logger.warning('add data not provided in env')
            logger.warning('app_id=%s', app_id)
            logger.warning('sso_signup_url=%s', sso_account_profile_url)
            
            return render(request, 'login/redirect-to-login-error.html')
        
        # encrypt account data
        cipher = Fernet(app_secret.encode())

        account_data = {
            'id': user.profile.sso_user_id,
            'exp': (timezone.now() + timedelta(hours=3)).isoformat() #TODO reduce exp in prod
        }
        
        account_data_str = json.dumps(account_data).encode('utf-8')

        encrypted_data = cipher.encrypt(account_data_str)
        encrypted_data_str = encrypted_data.decode('utf-8')
        
        # redirect to SSO app
        url = f'{sso_account_profile_url}?app_id={app_id}&account={encrypted_data_str}'
        return redirect(url)
    
    return render(request, 'profile/my-profile.html', {'user': user})

def logout_view(request):
    if request.user.is_authenticated:
        logout(request)

    return redirect('home') 
