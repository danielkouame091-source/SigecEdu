"""Database tables (SQLAlchemy). One class = one table."""
from sqlalchemy import Boolean, Column, Enum, Float, Integer, String

from database import Base
from enums import StatutAssiduite


class Eleve(Base):
    """A student and his/her attendance summary."""
    __tablename__ = "eleves"

    id = Column(Integer, primary_key=True, index=True)
    matricule = Column(String(50), unique=True, index=True, nullable=False)  # student ID, unique
    nom = Column(String(100), nullable=False)                                # last name
    prenoms = Column(String(150), nullable=False)                            # first names
    taux_assiduite = Column(Float, default=100.0)                            # attendance rate, in %
    statut_assiduite = Column(Enum(StatutAssiduite), default=StatutAssiduite.REGULIER)
    eligible_examen = Column(Boolean, default=True)                          # allowed to sit the exam?


class Enseignant(Base):
    """A teacher."""
    __tablename__ = "enseignants"

    id = Column(Integer, primary_key=True, index=True)
    numero_te = Column(String(50), unique=True, index=True, nullable=False)  # teacher ID, unique
    nom = Column(String(100), nullable=False)
    prenoms = Column(String(150), nullable=False)
    biometrie_enregistree = Column(Boolean, default=False)                   # fingerprint/face enrolled?


class Utilisateur(Base):
    """A person who can log in to the system (for example an administrator)."""
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)                    # never the real password
    role = Column(String(30), nullable=False, default="USER")                # e.g. ADMIN
    nom = Column(String(100), nullable=False)
    prenoms = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True)
