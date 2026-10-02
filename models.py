from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
from enums import StatutPresence, StatutAssiduite, StatutSeance

class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, index=True)
    prenoms = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="AGENT")
    is_active = Column(Boolean, default=True)

class Eleve(Base):
    __tablename__ = "eleves"

    id = Column(Integer, primary_key=True, index=True)
    matricule = Column(String, unique=True, index=True)
    nom = Column(String, index=True)
    prenoms = Column(String)
    taux_assiduite = Column(Float, default=100.0)
    statut_assiduite = Column(SQLEnum(StatutAssiduite), default=StatutAssiduite.REGULIER)
    eligible_examen = Column(Boolean, default=True)

class Enseignant(Base):
    __tablename__ = "enseignants"

    id = Column(Integer, primary_key=True, index=True)
    numero_te = Column(String, unique=True, index=True)
    nom = Column(String, index=True)
    prenoms = Column(String)
    biometrie_enregistree = Column(Boolean, default=False)

class PointageCours(Base):
    __tablename__ = "pointages_cours"

    id = Column(Integer, primary_key=True, index=True)
    enseignant_id = Column(Integer, ForeignKey("enseignants.id"))
    date_pointage = Column(DateTime, default=datetime.utcnow)
    statut_seance = Column(SQLEnum(StatutSeance), default=StatutSeance.DISPENSE)
    service_fait_valide = Column(Boolean, default=False)
