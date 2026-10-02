from sqlalchemy.orm import Session
import models
import schemas

def get_eleve_by_matricule(db: Session, matricule: str):
    return db.query(models.Eleve).filter(models.Eleve.matricule == matricule).first()

def create_eleve(db: Session, eleve: schemas.EleveBase):
    db_eleve = models.Eleve(
        matricule=eleve.matricule,
        nom=eleve.nom,
        prenoms=eleve.prenoms
    )
    db.add(db_eleve)
    db.commit()
    db.refresh(db_eleve)
    return db_eleve

def get_enseignant_by_te(db: Session, numero_te: str):
    return db.query(models.Enseignant).filter(models.Enseignant.numero_te == numero_te).first()

def create_enseignant(db: Session, enseignant: schemas.EnseignantBase):
    db_enseignant = models.Enseignant(
        numero_te=enseignant.numero_te,
        nom=enseignant.nom,
        prenoms=enseignant.prenoms
    )
    db.add(db_enseignant)
    db.commit()
    db.refresh(db_enseignant)
    return db_enseignant
