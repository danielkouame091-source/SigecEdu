import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, Enum
from database import Base

class StatutAssiduiteEnum(enum.Enum):
    REGULIER = "Régulier"
    IRREGULIER = "Irrégulier"
    ABSENT = "Absent"
    EXCLU = "Exclu"

class Eleve(Base):
    __tablename__ = "eleves"

    id = Column(Integer, primary_key=True, index=True)
    matricule = Column(String(50), unique=True, index=True, nullable=False)
    nom = Column(String(100), nullable=False)
    prenoms = Column(String(150), nullable=False)
    taux_assiduite = Column(Float, default=100.0)
    statut_assiduite = Column(Enum(StatutAssiduiteEnum), default=StatutAssiduiteEnum.REGULIER)
    eligible_examen = Column(Boolean, default=True)
