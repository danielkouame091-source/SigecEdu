"""Sécurité : hachage bcrypt, JWT, signature HMAC des preuves."""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    """Hache un mot de passe avec bcrypt (jamais en clair !)."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash bcrypt."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str, expires_minutes: Optional[int] = None) -> str:
    """Génère un JWT signé."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Décode et vérifie un JWT."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Token invalide : {e}")


def sign_proof(data: str) -> str:
    """Signature HMAC-SHA256 d'une preuve (immuabilité pointages/présences)."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_proof(data: str, signature: str) -> bool:
    """Vérifie qu'une preuve n'a pas été falsifiée."""
    expected = sign_proof(data)
    return hmac.compare_digest(expected, signature)


def hash_biometric(biometric_data: str) -> str:
    """Hash d'une donnée biométrique (empreinte / visage)."""
    return hashlib.sha256(biometric_data.encode("utf-8")).hexdigest()
