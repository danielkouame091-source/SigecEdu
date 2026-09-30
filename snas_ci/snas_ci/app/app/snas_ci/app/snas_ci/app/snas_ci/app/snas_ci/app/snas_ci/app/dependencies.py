"""Dépendances FastAPI : récupération de l'utilisateur connecté."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Utilisateur, UserRole, Enseignant
from app.security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Utilisateur:
    """Récupère l'utilisateur à partir du token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
    if not user or not user.actif:
        raise credentials_exception
    return user


def require_role(*roles: UserRole):
    """Fabrique une dépendance qui exige un rôle particulier."""
    def _checker(user: Utilisateur = Depends(get_current_user)) -> Utilisateur:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle insuffisant. Requis : {[r.value for r in roles]}",
            )
        return user
    return _checker


def get_current_enseignant(
    user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Enseignant:
    """Récupère l'enseignant lié à l'utilisateur connecté."""
    ens = db.query(Enseignant).filter(Enseignant.utilisateur_id == user.id).first()
    if not ens:
        raise HTTPException(status_code=403, detail="Utilisateur non enseignant")
    return ens
