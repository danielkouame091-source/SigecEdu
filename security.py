"""security.py - Argon2id, jetons JWT et contrôle strict des rôles."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from config import get_settings
from enums import RoleUtilisateur

_ph = PasswordHasher()                       # Argon2id, paramètres par défaut d'argon2-cffi
_HASH_FACTICE = _ph.hash("hash-factice-temps-constant")


# --- Mots de passe ----------------------------------------------------------
def hacher(mot_de_passe: str) -> str:
    return _ph.hash(mot_de_passe)


def verifier(mot_de_passe: str, hash_stocke: str) -> bool:
    try:
        return _ph.verify(hash_stocke, mot_de_passe)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verifier_factice(mot_de_passe: str) -> None:
    """Consomme le même temps qu'une vraie vérification (anti-énumération des comptes)."""
    verifier(mot_de_passe, _HASH_FACTICE)


def doit_rehacher(hash_stocke: str) -> bool:
    return _ph.check_needs_rehash(hash_stocke)


# --- Jetons ------------------------------------------------------------------
class Claims(BaseModel):
    sub: uuid.UUID
    role: RoleUtilisateur
    etab: uuid.UUID | None = None
    struct: uuid.UUID | None = None


def creer_jeton(utilisateur) -> tuple[str, int]:
    cfg = get_settings()
    maintenant = datetime.now(timezone.utc)
    duree = timedelta(minutes=cfg.jwt_expiration_min)
    payload = {
        "sub": str(utilisateur.id),
        "role": utilisateur.role.value,
        "etab": str(utilisateur.etablissement_id) if utilisateur.etablissement_id else None,
        "struct": str(utilisateur.structure_id) if utilisateur.structure_id else None,
        "iat": int(maintenant.timestamp()),
        "exp": int((maintenant + duree).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, cfg.jwt_secret, algorithm="HS256"), int(duree.total_seconds())


_bearer = HTTPBearer(auto_error=False)


def get_claims(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Claims:
    non_auth = HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise",
                             headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise non_auth
    try:
        data = jwt.decode(
            creds.credentials, get_settings().jwt_secret, algorithms=["HS256"],
            options={"require": ["exp", "sub", "role"]},
        )
        return Claims(**{k: data.get(k) for k in ("sub", "role", "etab", "struct")})
    except (jwt.PyJWTError, ValueError):
        raise non_auth


def exiger_roles(*roles: RoleUtilisateur):
    """Dépendance FastAPI : refuse (403) tout rôle hors liste. Liste blanche, jamais liste noire."""
    def _controle(claims: Claims = Depends(get_claims)) -> Claims:
        if claims.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle insuffisant pour cette opération")
        return claims
    return _controle
