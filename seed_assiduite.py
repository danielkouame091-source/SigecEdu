import sys
from database import SessionLocal
from models import Eleve
from enums import StatutAssiduite

def seed_donnees():
    db = SessionLocal()
    try:
        # Vérifier si des élèves existent déjà
        existing = db.query(Eleve).first()
        if existing:
            print("Des élèves existent déjà dans la base. Seed ignoré.")
            return

        eleves_test = [
            Eleve(matricule="ELEVE001", nom="Kouassi", prenoms="Aya", taux_assiduite=95.0, statut_assiduite=StatutAssiduite.REGULIER, eligible_examen=True),
            Eleve(matricule="ELEVE002", nom="Traore", prenoms="Mamadou", taux_assiduite=82.5, statut_assiduite=StatutAssiduite.REGULIER, eligible_examen=True),
            Eleve(matricule="ELEVE003", nom="Konan", prenoms="Affoue", taux_assiduite=68.0, statut_assiduite=StatutAssiduite.EXCLU, eligible_examen=False),
            Eleve(matricule="ELEVE004", nom="Diallo", prenoms="Ibrahim", taux_assiduite=90.0, statut_assiduite=StatutAssiduite.REGULIER, eligible_examen=True),
        ]

        db.add_all(eleves_test)
        db.commit()
        print("Succès : 4 élèves de test (Session DEMO-BEPC) ont été insérés avec succès !")
    except Exception as e:
        db.rollback()
        print(f"Erreur lors du seed : {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_donnees()
