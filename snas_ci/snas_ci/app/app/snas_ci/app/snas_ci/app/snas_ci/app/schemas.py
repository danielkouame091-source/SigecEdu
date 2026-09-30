"""Schémas Pydantic : validation stricte des entrées/sorties API."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models import UserRole, SecteurType, CycleType


class UtilisateurCreate(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(min_length=8, max_length=128)
    role: UserRole
    nom: str = Field(min_length=1, max_length=100)
    prenoms: str = Field(min_length=1, max_length=150)
    telephone: Optional[str] = Field(default=None, max_length=20)
    date_naissance: Optional[date] = None


class UtilisateurOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: Optional[str]
    role: UserRole
    nom: str
    prenoms: str
    actif: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    mot_de_passe: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    utilisateur_id: str
