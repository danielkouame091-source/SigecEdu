"""models.py - Modèles SQLAlchemy 2.0 (miroir de schema_maitre.sql + schema_salaires.sql).

Le schéma est créé par les scripts SQL (pas par create_all) : les colonnes calculées
ou remplies par trigger sont donc déclarées `FetchedValue` / `Computed` pour que l'ORM
ne tente jamais de les écrire et relise la valeur décidée par la base.
"""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean, Computed, Date, DateTime, FetchedValue, ForeignKey, Integer,
    LargeBinary, Numeric, SmallInteger, String, Text,
)
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from enums import (
    NiveauEnseignement, RoleUtilisateur, SecteurEtablissement, StatutAssiduite,
    StatutEmploi, StatutPresence, StatutRetenue, StatutSeance, TypePointage,
)


def _enum(cls, nom: str) -> PGEnum:
    return PGEnum(cls, name=nom, create_type=False)


def _pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _fk(table: str, **kw):
    return mapped_column(UUID(as_uuid=True), ForeignKey(f"{table}.id"), **kw)


_TS = DateTime(timezone=True)


class ParametreSysteme(Base):
    __tablename__ = "parametres_systeme"
    cle: Mapped[str] = mapped_column(String, primary_key=True)
    valeur: Mapped[Decimal] = mapped_column(Numeric)


class StructureAdministrative(Base):
    __tablename__ = "structures_administratives"
    id: Mapped[uuid.UUID] = _pk()
    parent_id: Mapped[uuid.UUID | None] = _fk("structures_administratives")
    code: Mapped[str] = mapped_column(String, unique=True)
    nom: Mapped[str] = mapped_column(String)


class Etablissement(Base):
    __tablename__ = "etablissements"
    id: Mapped[uuid.UUID] = _pk()
    structure_id: Mapped[uuid.UUID] = _fk("structures_administratives")
    code_etablissement: Mapped[str] = mapped_column(String, unique=True)
    nom: Mapped[str] = mapped_column(String)
    secteur: Mapped[SecteurEtablissement] = mapped_column(_enum(SecteurEtablissement, "secteur_etablissement"))
    niveau: Mapped[NiveauEnseignement] = mapped_column(_enum(NiveauEnseignement, "niveau_enseignement"))
    numero_agrement: Mapped[str | None] = mapped_column(String)
    commune: Mapped[str | None] = mapped_column(String)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id: Mapped[uuid.UUID] = _pk()
    role: Mapped[RoleUtilisateur] = mapped_column(_enum(RoleUtilisateur, "role_utilisateur"))
    etablissement_id: Mapped[uuid.UUID | None] = _fk("etablissements")
    structure_id: Mapped[uuid.UUID | None] = _fk("structures_administratives")
    email: Mapped[str | None] = mapped_column(String)
    telephone: Mapped[str | None] = mapped_column(String)
    mot_de_passe_hash: Mapped[str] = mapped_column(String)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    tentatives_echec: Mapped[int] = mapped_column(Integer, default=0)
    verrouille_jusqua: Mapped[dt.datetime | None] = mapped_column(_TS)
    derniere_connexion: Mapped[dt.datetime | None] = mapped_column(_TS)


class TerminalBiometrique(Base):
    __tablename__ = "terminaux_biometriques"
    id: Mapped[uuid.UUID] = _pk()
    etablissement_id: Mapped[uuid.UUID] = _fk("etablissements")
    numero_serie: Mapped[str] = mapped_column(String, unique=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Professeur(Base):
    __tablename__ = "professeurs"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = _pk()
    utilisateur_id: Mapped[uuid.UUID | None] = _fk("utilisateurs", unique=True)
    etablissement_id: Mapped[uuid.UUID] = _fk("etablissements")
    nom: Mapped[str] = mapped_column(String)
    prenoms: Mapped[str] = mapped_column(String)
    specialite: Mapped[str | None] = mapped_column(String)
    statut_emploi: Mapped[StatutEmploi] = mapped_column(_enum(StatutEmploi, "statut_emploi"))
    # copie automatique du secteur de l'établissement (trigger)
    secteur: Mapped[SecteurEtablissement] = mapped_column(
        _enum(SecteurEtablissement, "secteur_etablissement"), server_default=FetchedValue()
    )
    matricule_fonction_publique: Mapped[str | None] = mapped_column(String, unique=True)
    gabarit_biometrique_chiffre: Mapped[bytes | None] = mapped_column(LargeBinary)
    biometrie_consentement_le: Mapped[dt.datetime | None] = mapped_column(_TS)
    taux_horaire_fcfa: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Classe(Base):
    __tablename__ = "classes"
    id: Mapped[uuid.UUID] = _pk()
    etablissement_id: Mapped[uuid.UUID] = _fk("etablissements")
    annee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    libelle: Mapped[str] = mapped_column(String)
    niveau: Mapped[str] = mapped_column(String)


class Eleve(Base):
    __tablename__ = "eleves"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = _pk()
    roll_number: Mapped[str] = mapped_column(String, unique=True, server_default=FetchedValue())
    utilisateur_id: Mapped[uuid.UUID | None] = _fk("utilisateurs", unique=True)
    nom: Mapped[str] = mapped_column(String)
    prenoms: Mapped[str] = mapped_column(String)
    date_naissance: Mapped[dt.date] = mapped_column(Date)
    lieu_naissance: Mapped[str | None] = mapped_column(String)
    sexe: Mapped[str | None] = mapped_column(String(1))


class Inscription(Base):
    __tablename__ = "inscriptions"
    id: Mapped[uuid.UUID] = _pk()
    eleve_id: Mapped[uuid.UUID] = _fk("eleves")
    classe_id: Mapped[uuid.UUID] = _fk("classes")
    annee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    date_inscription: Mapped[dt.date] = mapped_column(Date, server_default=FetchedValue())
    date_sortie: Mapped[dt.date | None] = mapped_column(Date)
    nb_seances_appelees: Mapped[int] = mapped_column(Integer, default=0)
    nb_presences: Mapped[int] = mapped_column(Integer, default=0)
    taux_assiduite: Mapped[Decimal] = mapped_column(Numeric(5, 2), Computed("0", persisted=True))
    statut_assiduite: Mapped[StatutAssiduite] = mapped_column(
        _enum(StatutAssiduite, "statut_assiduite"), default=StatutAssiduite.REGULIER
    )


class Seance(Base):
    __tablename__ = "seances_cours"
    id: Mapped[uuid.UUID] = _pk()
    emploi_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    classe_id: Mapped[uuid.UUID] = _fk("classes")
    professeur_prevu_id: Mapped[uuid.UUID] = _fk("professeurs")
    professeur_effectif_id: Mapped[uuid.UUID | None] = _fk("professeurs")
    date_seance: Mapped[dt.date] = mapped_column(Date)
    debut: Mapped[dt.datetime] = mapped_column(_TS)
    fin: Mapped[dt.datetime] = mapped_column(_TS)
    statut: Mapped[StatutSeance] = mapped_column(_enum(StatutSeance, "statut_seance"), default=StatutSeance.PLANIFIE)
    retard_min: Mapped[int | None] = mapped_column(Integer)
    motif_statut: Mapped[str | None] = mapped_column(Text)
    evalue_le: Mapped[dt.datetime | None] = mapped_column(_TS)


class Remplacement(Base):
    __tablename__ = "remplacements"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = _pk()
    seance_id: Mapped[uuid.UUID] = _fk("seances_cours", unique=True)
    professeur_remplacant_id: Mapped[uuid.UUID] = _fk("professeurs")
    declare_par: Mapped[uuid.UUID | None] = _fk("utilisateurs")
    # posés par le trigger serveur : horloge serveur, préavis >= 24 h calculé par la base
    declare_le: Mapped[dt.datetime] = mapped_column(_TS, server_default=FetchedValue())
    conforme_preavis: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())


class PointageProfesseur(Base):
    __tablename__ = "pointages_professeurs"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = _pk()
    professeur_id: Mapped[uuid.UUID] = _fk("professeurs")
    seance_id: Mapped[uuid.UUID] = _fk("seances_cours")
    type: Mapped[TypePointage] = mapped_column(_enum(TypePointage, "type_pointage"))
    horodatage: Mapped[dt.datetime] = mapped_column(_TS)
    recu_le: Mapped[dt.datetime] = mapped_column(_TS, server_default=FetchedValue())
    terminal_id: Mapped[uuid.UUID | None] = _fk("terminaux_biometriques")
    score_correspondance: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    signature_terminal: Mapped[str | None] = mapped_column(String)


class PresenceEleve(Base):
    """Table partitionnée par date_seance : la clé primaire est composite."""
    __tablename__ = "presences_eleves"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date_seance: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    seance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    inscription_id: Mapped[uuid.UUID] = _fk("inscriptions")
    ordre_appel: Mapped[int] = mapped_column(Integer)
    statut: Mapped[StatutPresence] = mapped_column(_enum(StatutPresence, "statut_presence"))
    horodatage: Mapped[dt.datetime] = mapped_column(_TS)
    saisi_par: Mapped[uuid.UUID | None] = _fk("utilisateurs")


class SessionExamen(Base):
    __tablename__ = "sessions_examens"
    id: Mapped[uuid.UUID] = _pk()
    annee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    code: Mapped[str] = mapped_column(String)
    libelle: Mapped[str] = mapped_column(String)
    niveau_concerne: Mapped[str] = mapped_column(String)
    date_debut: Mapped[dt.date] = mapped_column(Date)
    date_fin: Mapped[dt.date] = mapped_column(Date)


class Convocation(Base):
    """taux, seuil, bloque, hash et date de génération sont calculés PAR LA BASE (trigger)
    et inaltérables ensuite : l'ORM ne les écrit jamais."""
    __tablename__ = "convocations_examens"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = _pk()
    session_id: Mapped[uuid.UUID] = _fk("sessions_examens")
    inscription_id: Mapped[uuid.UUID] = _fk("inscriptions")
    taux_assiduite_fige: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default=FetchedValue())
    seuil_applique: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default=FetchedValue())
    bloque: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    hash_qr: Mapped[str] = mapped_column(String, server_default=FetchedValue())
    genere_le: Mapped[dt.datetime] = mapped_column(_TS, server_default=FetchedValue())
    centre_examen_id: Mapped[uuid.UUID | None] = _fk("etablissements")
    numero_table: Mapped[str | None] = mapped_column(String)
    imprime_le: Mapped[dt.datetime | None] = mapped_column(_TS)


class RetenueSalaire(Base):
    __tablename__ = "retenues_salaire"
    id: Mapped[uuid.UUID] = _pk()
    professeur_id: Mapped[uuid.UUID] = _fk("professeurs")
    seance_id: Mapped[uuid.UUID] = _fk("seances_cours", unique=True)
    duree_minutes: Mapped[int] = mapped_column(Integer)
    taux_horaire_fcfa: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    montant_fcfa: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    secteur: Mapped[SecteurEtablissement] = mapped_column(_enum(SecteurEtablissement, "secteur_etablissement"))
    statut: Mapped[StatutRetenue] = mapped_column(_enum(StatutRetenue, "statut_retenue"), server_default=FetchedValue())
    cree_le: Mapped[dt.datetime] = mapped_column(_TS, server_default=FetchedValue())
    contestable_jusqua: Mapped[dt.datetime] = mapped_column(_TS)
    motif_contestation: Mapped[str | None] = mapped_column(Text)
    motif_decision: Mapped[str | None] = mapped_column(Text)
    decide_par: Mapped[uuid.UUID | None] = _fk("utilisateurs")
    decide_le: Mapped[dt.datetime | None] = mapped_column(_TS)
