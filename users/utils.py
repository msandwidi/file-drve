from cryptography.fernet import Fernet, InvalidToken
import random
import string
import base64
import logging

logger = logging.getLogger(__name__)

def random_string(length=16):
    """
    Generate random username and password
    """

    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def decrypt_data(encrypted_data, secret, ttl=60):
    """
    Decrypt encrypted data using Fernet
    """
    
    cipher = Fernet(secret.encode())
    
    try:
        return cipher.decrypt(encrypted_data, ttl=ttl).decode('utf-8')
    except InvalidToken as e:
        logger.error(f'Unable to decrypt data: Invalid token - {e}')
        return None
    except Exception as e:
        logger.error(f'Unexpected error during decryption: {e}')
        return None
