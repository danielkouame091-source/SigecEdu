"""Crée les données de test : enseignant, classe, créneau."""
from datetime import date, time
from app.database import SessionLocal
from app.models import (
    Region, DRE, Etablissement, Utilisateur, Enseignant, Classe, Creneau,
    SecteurType, CycleType
)


def main():
    db = SessionLocal()
    try:
        region = db.query(Region).filter(Region.code == "ABJ").first()
        dre = db.query(DRE).filter(DRE.code == "DRE-ABJ-1").first()
        etab = db.query(Etablissement).filter(Etablissement.code_men == "CI-ABJ-001").first()

        user = db.query(Utilisateur).filter(Utilisateur.email == "prof1@snas.ci").first()
        if not user:
            raise RuntimeError("Utilisateur prof1@snas.ci introuvable.")

        ens = db.query(Enseignant).filter(Enseignant.utilisateur_id == user.id).first()
        if not ens:
            ens = Enseignant(
                utilisateur_id=user.id,
                matricule_fp="FP-2025-0001",
                etablissement_id=etab.id,
                secteur=SecteurType.PUBLIC,
                specialite="Mathematiques",
                taux_horaire_fcfa=2500,
                heures_contractuelles_semaine=18,
                date_prise_service=date(2020, 10, 1),
            )
            db.add(ens); db.commit(); db.refresh(ens)

        classe = db.query(Classe).filter(
            Classe.etablissement_id == etab.id,
            Classe.nom == "3eme-A",
            Classe.annee_scolaire == "2025-2026",
        ).first()
        if not classe:
            classe = Classe(
                etablissement_id=etab.id,
                nom="3eme-A",
                niveau="3EME",
                annee_scolaire="2025-2026",
                effectif_max=50,
            )
            db.add(classe); db.commit(); db.refresh(classe)

        creneau = db.query(Creneau).filter(
            Creneau.classe_id == classe.id,
            Creneau.jour_semaine == 1,
            Creneau.heure_debut == time(8, 0),
            Creneau.annee_scolaire == "2025-2026",
        ).first()
        if not creneau:
            creneau = Creneau(
                classe_id=classe.id,
                enseignant_id=ens.id,
                matiere="Mathematiques",
                jour_semaine=1,
                heure_debut=time(8, 0),
                heure_fin=time(10, 0),
                salle="B-12",
                annee_scolaire="2025-2026",
            )
            db.add(creneau); db.commit(); db.refresh(creneau)

        print("=" * 60)
        print("  DONNEES DE TEST PRETES")
        print("=" * 60)
        print(f"  Etablissement : {etab.nom}")
        print(f"  Enseignant    : {user.nom} {user.prenoms}")
        print(f"  Classe        : {classe.nom}")
        print(f"  Creneau       : {creneau.matiere} jour {creneau.jour_semaine}")
        print()
        print(f"  ID ENSEIGNANT = {ens.id}")
        print(f"  ID CRENEAU    = {creneau.id}")
        print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
