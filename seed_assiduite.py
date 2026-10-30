"""Fill the database with 4 fictional students so you can try the API right away.
Usage:  python seed_assiduite.py   (does nothing if students already exist)."""
from database import Base, SessionLocal, engine
from enums import StatutAssiduite
from models import Eleve


def seed_donnees():
    Base.metadata.create_all(bind=engine)   # make sure the tables exist
    db = SessionLocal()
    try:
        # Do nothing if the database already contains students
        if db.query(Eleve).first():
            print("Students already exist in the database. Seed skipped.")
            return

        test_students = [
            Eleve(matricule="ELEVE001", nom="Kouassi", prenoms="Aya", taux_assiduite=95.0,
                  statut_assiduite=StatutAssiduite.REGULIER, eligible_examen=True),
            Eleve(matricule="ELEVE002", nom="Traore", prenoms="Mamadou", taux_assiduite=82.5,
                  statut_assiduite=StatutAssiduite.REGULIER, eligible_examen=True),
            Eleve(matricule="ELEVE003", nom="Konan", prenoms="Affoue", taux_assiduite=68.0,
                  statut_assiduite=StatutAssiduite.EXCLU, eligible_examen=False),
            Eleve(matricule="ELEVE004", nom="Diallo", prenoms="Ibrahim", taux_assiduite=90.0,
                  statut_assiduite=StatutAssiduite.REGULIER, eligible_examen=True),
        ]

        db.add_all(test_students)
        db.commit()
        print("Success: 4 fictional test students (DEMO-BEPC session) were inserted!")
    except Exception as e:
        db.rollback()
        print(f"Error during seed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_donnees()
