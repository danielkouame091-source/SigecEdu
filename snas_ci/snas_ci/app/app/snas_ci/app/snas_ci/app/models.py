"""Modèles SQLAlchemy = tables de la base de données."""
import enum
import uuid
from datetime import datetime, date, time

from sqlalchemy import (
    String, Integer, Boolean, Date, Time, DateTime, Numeric,
    ForeignKey, UniqueConstraint, CheckConstraint, Text, Enum as SAEnum,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    """Génère un UUID v4 sous forme de chaîne."""
    return str(uuid.uuid4())


# ============================================================
#  ÉNUMÉRATIONS (valeurs strictes, impossibles à falsifier)
# ============================================================

class SecteurType(str, enum.Enum):
    PUBLIC = "PUBLIC"
    PRIVE = "PRIVE"


class CycleType(str, enum.Enum):
    PRIMAIRE = "PRIMAIRE"
    SECONDAIRE_1ER = "SECONDAIRE_1ER"
    SECONDAIRE_2ND = "SECONDAIRE_2ND"
    SUPERIEUR = "SUPERIEUR"
    CONCOURS = "CONCOURS"


class ExamenType(str, enum.Enum):
    CEPE = "CEPE"
    BEPC = "BEPC"
    BAC = "BAC"
    BTS = "BTS"
    CONCOURS_FP = "CONCOURS_FP"


class UserRole(str, enum.Enum):
    ENSEIGNANT = "ENSEIGNANT"
    DIRECTEUR = "DIRECTEUR"
    DRE = "DRE"
    ADMIN_NATIONAL = "ADMIN_NATIONAL"
    SURVEILLANT = "SURVEILLANT"
    ELEVE = "ELEVE"
    PARENT = "PARENT"


class PointageStatut(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    RETARD = "RETARD"
    REMPLACE = "REMPLACE"
    COURS_NON_DISPENSE = "COURS_NON_DISPENSE"


class PresenceStatut(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    RETARD = "RETARD"
    ABSENT_JUSTIFIE = "ABSENT_JUSTIFIE"
    ABSENT_NON_JUSTIFIE = "ABSENT_NON_JUSTIFIE"


class JustifStatut(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE = "VALIDE"
    REJETE = "REJETE"
    EXPIRE = "EXPIRE"


class ConvocationStatut(str, enum.Enum):
    BLOQUEE = "BLOQUEE"
    AUTORISEE = "AUTORISEE"
    ANNULEE = "ANNULEE"


# ============================================================
#  1. RÉFÉRENTIELS GÉOGRAPHIQUES
# ============================================================

class Region(Base):
    __tablename__ = "region"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dres: Mapped[list["DRE"]] = relationship(back_populates="region")


class DRE(Base):
    """Direction Régionale de l'Éducation."""
    __tablename__ = "dre"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    region_id: Mapped[str] = mapped_column(ForeignKey("region.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(150), nullable=False)

    # ⚠️ AUCUN pouvoir de modification des absences (anti-corruption)
    peut_modifier_absences: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    region: Mapped["Region"] = relationship(back_populates="dres")
    etablissements: Mapped[list["Etablissement"]] = relationship(back_populates="dre")


# ============================================================
#  2. ÉTABLISSEMENTS
# ============================================================

class Etablissement(Base):
    __tablename__ = "etablissement"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    code_men: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    secteur: Mapped[SecteurType] = mapped_column(SAEnum(SecteurType), nullable=False)
    cycle: Mapped[CycleType] = mapped_column(SAEnum(CycleType), nullable=False)
    dre_id: Mapped[str] = mapped_column(ForeignKey("dre.id"), nullable=False)
    adresse: Mapped[str | None] = mapped_column(Text, nullable=True)
    telephone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    # 🔒 RÈGLE ANTI-CORRUPTION : le privé ne peut PAS valider de convocation
    peut_valider_convocation: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    dre: Mapped["DRE"] = relationship(back_populates="etablissements")
    classes: Mapped[list["Classe"]] = relationship(back_populates="etablissement")
    enseignants: Mapped[list["Enseignant"]] = relationship(back_populates="etablissement")


# ============================================================
#  3. UTILISATEURS
# ============================================================

class Utilisateur(Base):
    __tablename__ = "utilisateur"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    telephone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenoms: Mapped[str] = mapped_column(String(150), nullable=False)
    date_naissance: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Biométrie (jamais la donnée brute en clair)
    empreinte_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    face_embedding: Mapped[bytes | None] = mapped_column(nullable=True)

    mfa_actif: Mapped[bool] = mapped_column(Boolean, default=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    derniere_connexion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    enseignant: Mapped["Enseignant | None"] = relationship(back_populates="utilisateur")


# ============================================================
#  4. ENSEIGNANTS
# ============================================================

class Enseignant(Base):
    __tablename__ = "enseignant"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    utilisateur_id: Mapped[str] = mapped_column(
        ForeignKey("utilisateur.id"), unique=True, nullable=False
    )
    matricule_fp: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissement.id"), nullable=False)

    # Dénormalisé pour performance + règle Public/Privé
    secteur: Mapped[SecteurType] = mapped_column(SAEnum(SecteurType), nullable=False)

    specialite: Mapped[str | None] = mapped_column(String(100), nullable=True)
    taux_horaire_fcfa: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    heures_contractuelles_semaine: Mapped[int] = mapped_column(Integer, default=18)
    date_prise_service: Mapped[date] = mapped_column(Date, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    utilisateur: Mapped["Utilisateur"] = relationship(back_populates="enseignant")
    etablissement: Mapped["Etablissement"] = relationship(back_populates="enseignants")

    # ⚠️ foreign_keys explicite car 2 FK vers enseignant (enseignant_id + remplacant_id)
    pointages: Mapped[list["PointageEnseignant"]] = relationship(
        back_populates="enseignant",
        foreign_keys="PointageEnseignant.enseignant_id",
    )
    creneaux: Mapped[list["Creneau"]] = relationship(back_populates="enseignant")


# ============================================================
#  5. CLASSES
# ============================================================

class Classe(Base):
    __tablename__ = "classe"
    __table_args__ = (
        UniqueConstraint("etablissement_id", "nom", "annee_scolaire", name="uq_classe"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    etablissement_id: Mapped[str] = mapped_column(ForeignKey("etablissement.id"), nullable=False)
    nom: Mapped[str] = mapped_column(String(50), nullable=False)
    niveau: Mapped[str] = mapped_column(String(20), nullable=False)
    annee_scolaire: Mapped[str] = mapped_column(String(9), nullable=False)
    effectif_max: Mapped[int] = mapped_column(Integer, default=60)

    etablissement: Mapped["Etablissement"] = relationship(back_populates="classes")
    eleves: Mapped[list["Eleve"]] = relationship(back_populates="classe")
    creneaux: Mapped[list["Creneau"]] = relationship(back_populates="classe")


# ============================================================
#  6. ÉLÈVES (Roll Numbers - style Chandigarh University)
# ============================================================

class Eleve(Base):
    __tablename__ = "eleve"
    __table_args__ = (
        UniqueConstraint("classe_id", "roll_number", name="uq_roll_number"),
        CheckConstraint("sexe IN ('M','F')", name="ck_sexe"),
        CheckConstraint("roll_number > 0", name="ck_roll_positif"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    matricule_national: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    # 🎯 ID séquentiel par classe (appel rapide "Roll Number")
    roll_number: Mapped[int] = mapped_column(Integer, nullable=False)

    classe_id: Mapped[str] = mapped_column(ForeignKey("classe.id"), nullable=False)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenoms: Mapped[str] = mapped_column(String(150), nullable=False)
    date_naissance: Mapped[date] = mapped_column(Date, nullable=False)
    lieu_naissance: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sexe: Mapped[str] = mapped_column(String(1), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_telephone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 📊 Assiduité (matérialisée pour performance)
    taux_assiduite: Mapped[float] = mapped_column(Numeric(5, 2), default=100.00)
    seuil_atteint: Mapped[bool] = mapped_column(Boolean, default=True)
    bloque_convocation: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    classe: Mapped["Classe"] = relationship(back_populates="eleves")
    presences: Mapped[list["PresenceEleve"]] = relationship(back_populates="eleve")
    justificatifs: Mapped[list["Justificatif"]] = relationship(back_populates="eleve")
    convocations: Mapped[list["Convocation"]] = relationship(back_populates="eleve")

    @property
    def nom_complet(self) -> str:
        return f"{self.nom} {self.prenoms}"


Index("ix_eleve_bloque", Eleve.bloque_convocation)


# ============================================================
#  7. CRÉNEAUX (emploi du temps)
# ============================================================

class Creneau(Base):
    __tablename__ = "creneau"
    __table_args__ = (
        UniqueConstraint("classe_id", "jour_semaine", "heure_debut", "annee_scolaire", name="uq_creneau"),
        CheckConstraint("jour_semaine BETWEEN 1 AND 6", name="ck_jour"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    classe_id: Mapped[str] = mapped_column(ForeignKey("classe.id"), nullable=False)
    enseignant_id: Mapped[str] = mapped_column(ForeignKey("enseignant.id"), nullable=False)
    matiere: Mapped[str] = mapped_column(String(100), nullable=False)
    jour_semaine: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=Lundi
    heure_debut: Mapped[time] = mapped_column(Time, nullable=False)
    heure_fin: Mapped[time] = mapped_column(Time, nullable=False)
    salle: Mapped[str | None] = mapped_column(String(50), nullable=True)
    annee_scolaire: Mapped[str] = mapped_column(String(9), nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    classe: Mapped["Classe"] = relationship(back_populates="creneaux")
    enseignant: Mapped["Enseignant"] = relationship(back_populates="creneaux")
    pointages: Mapped[list["PointageEnseignant"]] = relationship(back_populates="creneau")
    presences: Mapped[list["PresenceEleve"]] = relationship(back_populates="creneau")


# ============================================================
#  8. POINTAGE DES ENSEIGNANTS (cœur du système)
# ============================================================

class PointageEnseignant(Base):
    __tablename__ = "pointage_enseignant"
    __table_args__ = (
        UniqueConstraint("enseignant_id", "creneau_id", "date_cours", name="uq_pointage"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    enseignant_id: Mapped[str] = mapped_column(ForeignKey("enseignant.id"), nullable=False)
    creneau_id: Mapped[str] = mapped_column(ForeignKey("creneau.id"), nullable=False)
    date_cours: Mapped[date] = mapped_column(Date, nullable=False)
    heure_pointage: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    statut: Mapped[PointageStatut] = mapped_column(SAEnum(PointageStatut), nullable=False)

    # Biométrie
    methode_verif: Mapped[str | None] = mapped_column(String(20), nullable=True)
    score_biometrique: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)

    # Remplacement (doit être validé 24h à l'avance)
    remplacant_id: Mapped[str | None] = mapped_column(ForeignKey("enseignant.id"), nullable=True)
    remplacement_valide: Mapped[bool] = mapped_column(Boolean, default=False)
    valide_24h_avant: Mapped[bool] = mapped_column(Boolean, default=False)

    # 🔒 Immuabilité (preuve cryptographique)
    hash_preuve: Mapped[str] = mapped_column(Text, nullable=False)
    signature_numerique: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Mode offline
    sync_offline: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    enseignant: Mapped["Enseignant"] = relationship(
        foreign_keys=[enseignant_id], back_populates="pointages"
    )
    creneau: Mapped["Creneau"] = relationship(back_populates="pointages")


Index("ix_pointage_statut", PointageEnseignant.statut)
Index("ix_pointage_ens_date", PointageEnseignant.enseignant_id, PointageEnseignant.date_cours)


# ============================================================
#  9. PRÉSENCE DES ÉLÈVES
# ============================================================

class PresenceEleve(Base):
    __tablename__ = "presence_eleve"
    __table_args__ = (
        UniqueConstraint("eleve_id", "creneau_id", "date_cours", name="uq_presence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleve.id"), nullable=False)
    creneau_id: Mapped[str] = mapped_column(ForeignKey("creneau.id"), nullable=False)
    date_cours: Mapped[date] = mapped_column(Date, nullable=False)

    statut: Mapped[PresenceStatut] = mapped_column(SAEnum(PresenceStatut), nullable=False)
    heure_appel: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Justificatif
    justificatif_id: Mapped[str | None] = mapped_column(
        ForeignKey("justificatif.id", use_alter=True, name="fk_pres_justif"),
        nullable=True
    )
    delai_justif_expire: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verrouille: Mapped[bool] = mapped_column(Boolean, default=False)

    # Immuabilité
    hash_preuve: Mapped[str] = mapped_column(Text, nullable=False)
    signature_numerique: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_offline: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    eleve: Mapped["Eleve"] = relationship(back_populates="presences")
    creneau: Mapped["Creneau"] = relationship(back_populates="presences")
    justificatif: Mapped["Justificatif | None"] = relationship(
        foreign_keys=[justificatif_id],
        post_update=True
    )


Index("ix_presence_eleve_date", PresenceEleve.eleve_id, PresenceEleve.date_cours)
Index("ix_presence_statut", PresenceEleve.statut)


# ============================================================
#  10. JUSTIFICATIFS D'ABSENCE (délai strict de 72h)
# ============================================================

class Justificatif(Base):
    __tablename__ = "justificatif"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleve.id"), nullable=False)
    motif: Mapped[str] = mapped_column(Text, nullable=False)
    fichier_url: Mapped[str] = mapped_column(Text, nullable=False)
    depose_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    statut: Mapped[JustifStatut] = mapped_column(
        SAEnum(JustifStatut), default=JustifStatut.EN_ATTENTE
    )
    traite_par: Mapped[str | None] = mapped_column(ForeignKey("utilisateur.id"), nullable=True)
    traite_le: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    commentaire: Mapped[str | None] = mapped_column(Text, nullable=True)

    eleve: Mapped["Eleve"] = relationship(back_populates="justificatifs")


# ============================================================
#  11. CONVOCATIONS + QR CODE
# ============================================================

class Convocation(Base):
    __tablename__ = "convocation"
    __table_args__ = (
        UniqueConstraint("eleve_id", "examen", "annee", name="uq_convocation"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    eleve_id: Mapped[str] = mapped_column(ForeignKey("eleve.id"), nullable=False)
    examen: Mapped[ExamenType] = mapped_column(SAEnum(ExamenType), nullable=False)
    annee: Mapped[str] = mapped_column(String(9), nullable=False)

    # 📸 Snapshot immuable du taux au moment de la génération
    taux_assiduite_snapshot: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    seuil_requis: Mapped[float] = mapped_column(Numeric(5, 2), default=85.00)

    statut: Mapped[ConvocationStatut] = mapped_column(SAEnum(ConvocationStatut), nullable=False)
    date_generation: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # QR code
    qr_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    qr_expire_le: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    qr_signature: Mapped[str] = mapped_column(Text, nullable=False)

    # Contrôle à l'entrée de l'examen
    scanne_le: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scanne_par: Mapped[str | None] = mapped_column(ForeignKey("utilisateur.id"), nullable=True)
    acces_autorise: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    eleve: Mapped["Eleve"] = relationship(back_populates="convocations")


Index("ix_convocation_statut", Convocation.statut)
Index("ix_convocation_qr", Convocation.qr_token)


# ============================================================
#  12. AUDIT LOG IMMUABLE (anti-corruption)
# ============================================================

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    acteur_id: Mapped[str | None] = mapped_column(ForeignKey("utilisateur.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entite_cible: Mapped[str] = mapped_column(String(50), nullable=False)
    entite_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_source: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Chaînage cryptographique (chaque log pointe sur le hash du précédent)
    hash_precedent: Mapped[str | None] = mapped_column(Text, nullable=True)
    hash_courant: Mapped[str] = mapped_column(Text, nullable=False)

    horodatage: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
#  13. FILE DE SYNCHRONISATION (mode offline)
# ============================================================

class SyncQueue(Base):
    __tablename__ = "sync_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appareil_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload_chiffre: Mapped[bytes] = mapped_column(nullable=False)  # AES-256
    type_evenement: Mapped[str] = mapped_column(String(50), nullable=False)
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    traite_le: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    statut: Mapped[str] = mapped_column(String(20), default="EN_ATTENTE")
    tentatives: Mapped[int] = mapped_column(Integer, default=0)
