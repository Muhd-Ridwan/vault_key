from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from config import settings

_fernet = Fernet(settings.fernet_key.encode())


def encrypt(plaintext: str) -> bytes:
    return _fernet.encrypt(plaintext.encode())


def decrypt(ciphertext: bytes) -> str:
    try:
        return _fernet.decrypt(ciphertext).decode()
    except InvalidToken:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt data. The encryption key may have changed.",
        )
