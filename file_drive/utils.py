from decouple import config, UndefinedValueError

REQUIRED_ENV_VARS = [
    # SSO vars
    'APP_SSO_PUBLIC_ID',
    'APP_SSO_SECRET',
    'APP_SSO_LOGIN_URL',
    'APP_SSO_SIGNUP_URL',
    'APP_SSO_ACCOUNT_PROFILE_URL',
    'APP_SSO_API_SESSION_VALIDATION_URL',

    # App vars
    'DEBUG',
    'DJANGO_SECRET_KEY',
    'DJANGO_ALLOWED_HOSTS',
    'APP_DEFAULT_SHORT_LINK_DOMAIN',
]

def check_required_env():
    """
    Check for required env variables
    """

    missing = []

    for var in REQUIRED_ENV_VARS:
        try:
            config(var)
            
        except UndefinedValueError:
            missing.append(var)

    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
