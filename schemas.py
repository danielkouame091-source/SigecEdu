from pydantic import BaseModel, EmailStr
from enums import StatutAssiduite, StatutSeance

class EleveBase(BaseModel):
    matricule: str
    nom: str
    prenoms: str

class EleveOut(EleveBase):
    id: int
    taux_assiduite: float
    statut_assiduite: StatutAssiduite
    eligible_examen: bool

    class Config:
        from_attributes = True

class EnseignantBase(BaseModel):
    numero_te: str
    nom: str
    prenoms: str

class EnseignantOut(EnseignantBase):
    id: int
    biometrie_enregistree: bool

    class Config:
        from_attributes = True
