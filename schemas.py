"""schemas.py - Schémas Pydantic v2 (validation stricte des entrées/sorties de l'API)."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import (
    AfterValidator, AwareDatetime, BaseModel, ConfigDict, EmailStr, Field,
    field_validator, model_validator,
)

from enums import (
    NiveauEnseignement, RoleUtilisateur, SecteurEtablissement, StatutAssiduite,
    StatutEmploi, StatutPresence, StatutRetenue, StatutSeance, TypePointage,
)

# ---------------------------------------------------------------------------
# Types réutilisables
# ---------------------------------------------------------------------------
_ROLL_RE = re.compile(r"^CI-(\d{2})-(\d{8,})-(\d{2})$")


def roll_number_valide(valeur: str) -> str:
    """Format CI-AA-NNNNNNNN-CC ; CC = NNNNNNNN mod 97 (détecte les fautes de frappe hors ligne)."""
    m = _ROLL_RE.match(valeur)
    if not m:
        raise ValueError("Roll Number invalide (format attendu : CI-AA-NNNNNNNN-CC)")
    if int(m.group(3)) != int(m.group(2)) % 97:
        raise ValueError("Clé de contrôle du Roll Number invalide")
    return valeur


RollNumber = Annotated[str, AfterValidator(roll_number_valide)]
HashQR = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class _Base(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class _Sortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Authentification & utilisateurs
# ---------------------------------------------------------------------------
class LoginIn(_Base):
    identifiant: str = Field(min_length=3, max_length=254)    # email ou téléphone
    mot_de_passe: str = Field(min_length=1, max_length=256)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UtilisateurCreate(_Base):
    role: RoleUtilisateur
    etablissement_id: UUID | None = None
    structure_id: UUID | None = None
    email: EmailStr | None = None
    telephone: str | None = Field(default=None, pattern=r"^\+?[0-9]{8,15}$")
    mot_de_passe: str = Field(min_length=12, max_length=256)

    @model_validator(mode="after")
    def _coherence(self):
        if self.email is None and self.telephone is None:
            raise ValueError("Un email ou un téléphone est obligatoire")
        if self.role == RoleUtilisateur.INSPECTEUR:
            if self.structure_id is None or self.etablissement_id is not None:
                raise ValueError("Un inspecteur est rattaché à une structure (et à aucun établissement)")
        elif self.role != RoleUtilisateur.ADMIN:
            if self.etablissement_id is None or self.structure_id is not None:
                raise ValueError("Ce rôle est rattaché à un établissement (et à aucune structure)")
        return self


class UtilisateurOut(_Sortie):
    id: UUID
    role: RoleUtilisateur
    etablissement_id: UUID | None
    structure_id: UUID | None
    email: str | None
    telephone: str | None
    actif: bool


# ---------------------------------------------------------------------------
# Établissements (Public / Privé)
# ---------------------------------------------------------------------------
class EtablissementCreate(_Base):
    structure_id: UUID
    code_etablissement: str = Field(min_length=3, max_length=30, pattern=r"^[A-Z0-9\-]+$")
    nom: str = Field(min_length=2, max_length=200)
    secteur: SecteurEtablissement
    niveau: NiveauEnseignement
    numero_agrement: str | None = Field(default=None, max_length=50)
    commune: str | None = Field(default=None, max_length=100)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _regles(self):
        if self.secteur == SecteurEtablissement.PRIVE and not self.numero_agrement:
            raise ValueError("Un établissement privé doit avoir un numéro d'agrément")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude et longitude vont ensemble")
        return self


class EtablissementOut(_Sortie):
    id: UUID
    structure_id: UUID
    code_etablissement: str
    nom: str
    secteur: SecteurEtablissement
    niveau: NiveauEnseignement
    numero_agrement: str | None
    commune: str | None
    actif: bool


# ---------------------------------------------------------------------------
# Professeurs
# ---------------------------------------------------------------------------
class ProfesseurCreate(_Base):
    etablissement_id: UUID
    utilisateur_id: UUID | None = None
    nom: str = Field(min_length=1, max_length=100)
    prenoms: str = Field(min_length=1, max_length=150)
    specialite: str | None = Field(default=None, max_length=100)
    statut_emploi: StatutEmploi
    matricule_fonction_publique: str | None = Field(default=None, max_length=30)
    taux_horaire_fcfa: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    @model_validator(mode="after")
    def _matricule(self):
        if self.statut_emploi == StatutEmploi.FONCTIONNAIRE and not self.matricule_fonction_publique:
            raise ValueError("Le matricule de la fonction publique est obligatoire pour un fonctionnaire")
        return self


class ProfesseurOut(_Sortie):
    id: UUID
    etablissement_id: UUID
    nom: str
    prenoms: str
    specialite: str | None
    statut_emploi: StatutEmploi
    secteur: SecteurEtablissement
    actif: bool


# ---------------------------------------------------------------------------
# Élèves
# ---------------------------------------------------------------------------
class EleveCreate(_Base):
    nom: str = Field(min_length=1, max_length=100)
    prenoms: str = Field(min_length=1, max_length=150)
    date_naissance: date
    lieu_naissance: str | None = Field(default=None, max_length=100)
    sexe: str | None = Field(default=None, pattern=r"^[MF]$")
    classe_id: UUID | None = None          # si fourni : inscription immédiate pour l'année de la classe

    @field_validator("date_naissance")
    @classmethod
    def _date_plausible(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("La date de naissance ne peut pas être dans le futur")
        if v.year < 1950:
            raise ValueError("Date de naissance invraisemblable")
        return v


class EleveOut(_Sortie):
    id: UUID
    roll_number: RollNumber
    nom: str
    prenoms: str
    date_naissance: date
    sexe: str | None


class EleveAppelOut(BaseModel):
    inscription_id: UUID
    roll_number: RollNumber
    nom: str
    prenoms: str


class ListeAppelOut(BaseModel):
    seance_id: UUID
    date_seance: date
    classe_id: UUID
    eleves: list[EleveAppelOut]


# ---------------------------------------------------------------------------
# Séances, remplacements, pointages professeurs
# ---------------------------------------------------------------------------
class SeanceOut(_Sortie):
    id: UUID
    classe_id: UUID
    professeur_prevu_id: UUID
    professeur_effectif_id: UUID | None
    date_seance: date
    debut: datetime
    fin: datetime
    statut: StatutSeance
    retard_min: int | None
    motif_statut: str | None


class RemplacementCreate(_Base):
    seance_id: UUID
    professeur_remplacant_id: UUID


class RemplacementOut(_Sortie):
    id: UUID
    seance_id: UUID
    professeur_remplacant_id: UUID
    declare_le: datetime
    conforme_preavis: bool


class PointageCreate(_Base):
    id: UUID | None = None                                  # UUID généré par le terminal (idempotence)
    professeur_id: UUID
    seance_id: UUID
    type: TypePointage
    horodatage: AwareDatetime                               # fuseau obligatoire
    terminal_id: UUID | None = None
    score_correspondance: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    signature_terminal: str | None = Field(default=None, max_length=512)


class PointageOut(_Sortie):
    id: UUID
    professeur_id: UUID
    seance_id: UUID
    type: TypePointage
    horodatage: datetime
    recu_le: datetime


class PointageResultat(BaseModel):
    pointage: PointageOut
    deja_enregistre: bool
    statut_seance: StatutSeance


# ---------------------------------------------------------------------------
# Impact salarial
# ---------------------------------------------------------------------------
class RetenueOut(_Sortie):
    id: UUID
    professeur_id: UUID
    seance_id: UUID
    duree_minutes: int
    taux_horaire_fcfa: Decimal
    montant_fcfa: Decimal
    secteur: SecteurEtablissement
    statut: StatutRetenue
    contestable_jusqua: datetime
    motif_contestation: str | None
    motif_decision: str | None


class ContestationIn(_Base):
    motif: str = Field(min_length=10, max_length=2000)


class DecisionRetenueIn(_Base):
    accepter: bool                      # True = retenue confirmée, False = annulée
    motif: str = Field(min_length=10, max_length=2000)


class EvaluationResultat(BaseModel):
    seances_non_dispensees: int
    retenues_creees: int
    retenues_annulees: int
    retenues_validees: int
    sans_taux_horaire: int              # séances non dispensées dont le professeur n'a pas de taux renseigné


# ---------------------------------------------------------------------------
# Synchronisation hors ligne des appels élèves
# ---------------------------------------------------------------------------
class AppelLigneSync(_Base):
    id: UUID                            # généré sur l'appareil : clé d'idempotence
    seance_id: UUID
    date_seance: date
    inscription_id: UUID
    roll_number: RollNumber
    ordre_appel: int = Field(ge=1, le=1000)
    statut: StatutPresence
    horodatage: AwareDatetime


class AppelSyncRequest(_Base):
    lot_id: UUID
    lignes: list[AppelLigneSync] = Field(min_length=1, max_length=500)


class LigneRejetee(BaseModel):
    id: UUID
    code: str
    raison: str


class AppelSyncResponse(BaseModel):
    lot_id: UUID
    acceptes: list[UUID]
    rejetes: list[LigneRejetee]


# ---------------------------------------------------------------------------
# Assiduité, convocations, QR
# ---------------------------------------------------------------------------
class AssiduiteOut(BaseModel):
    inscription_id: UUID
    seances_comptees: int
    presences: int
    taux: Decimal
    seuil: Decimal
    bloque_si_convoque_maintenant: bool
    statut: StatutAssiduite


class ConvocationCreate(_Base):
    session_id: UUID
    inscription_id: UUID


class ConvocationOut(_Sortie):
    id: UUID
    session_id: UUID
    inscription_id: UUID
    taux_assiduite_fige: Decimal
    seuil_applique: Decimal
    bloque: bool
    hash_qr: HashQR
    genere_le: datetime


class GenerationSessionOut(BaseModel):
    convocations_creees: int
    anomalies_integrite: list[UUID]


class QRVerifierIn(_Base):
    payload: str = Field(min_length=10, max_length=200)


class QRVerifierOut(BaseModel):
    valide: bool
    bloque: bool | None = None
    autorise_entree: bool
    roll_number: str | None = None
    nom: str | None = None
    prenoms: str | None = None
    raison: str | None = None
