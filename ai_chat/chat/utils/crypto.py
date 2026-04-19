from cryptography.fernet import Fernet
from django.conf import settings

def get_fernet():
    key = settings.CLOUD_CREDENTIALS_KEY
    if not key:
        raise ValueError("CLOUD_CREDENTIALS_KEY is not configured")
    return Fernet(key.encode())


def encrypt_value(value: str) -> str:
    if not value:
        return ""
    return get_fernet().encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    if not value:
        return ""
    return get_fernet().decrypt(value.encode()).decode()