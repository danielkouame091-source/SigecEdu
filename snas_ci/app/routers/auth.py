"""Routeur d'authentification : inscription + connexion."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Utilisateur
from app.schemas import UtilisateurCreate, UtilisateurOut, LoginRequest, TokenResponse
from app.security import hash_password, verify_password, create_access_token


router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=UtilisateurOut, status_code=201)
def register(payload: UtilisateurCreate, db: Session = Depends(get_db)):
    """Crée un nouvel utilisateur."""
    existing = db.query(Utilisateur).filter(Utilisateur.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    user = Utilisateur(
        email=payload.email,
        mot_de_passe_hash=hash_password(payload.mot_de_passe),
        role=payload.role,
        nom=payload.nom,
        prenoms=payload.prenoms,
        telephone=payload.telephone,
        date_naissance=payload.date_naissance,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Connexion : renvoie un JWT."""
    user = db.query(Utilisateur).filter(Utilisateur.email == payload.email).first()
    if not user or not verify_password(payload.mot_de_passe, user.mot_de_passe_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not user.actif:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(
        access_token=token,
        role=user.role,
        utilisateur_id=user.id,
    )
