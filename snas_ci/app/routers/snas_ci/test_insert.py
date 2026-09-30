"""Test rapide : insère une région, une DRE et un établissement."""
from app.database import SessionLocal
from app.models import Region, DRE, Etablissement, SecteurType, CycleType


def main():
    db = SessionLocal()
    try:
        abidjan = Region(code="ABJ", nom="Abidjan")
        db.add(abidjan)
        db.commit()
        db.refresh(abidjan)
        print(f"✅ Région créée : {abidjan.nom}")

        dre = DRE(region_id=abidjan.id, code="DRE-ABJ-1", nom="DRE Abidjan 1")
        db.add(dre)
        db.commit()
        db.refresh(dre)
        print(f"✅ DRE créée : {dre.nom}")

        etab = Etablissement(
            code_men="CI-ABJ-001",
            nom="Lycée Classique d'Abidjan",
            secteur=SecteurType.PUBLIC,
            cycle=CycleType.SECONDAIRE_2ND,
            dre_id=dre.id,
            adresse="Cocody, Abidjan",
        )
        db.add(etab)
        db.commit()
        db.refresh(etab)
        print(f"✅ Établissement créé : {etab.nom}")
        print(f"🔒 Peut valider convocation ? {etab.peut_valider_convocation}")
        assert etab.peut_valider_convocation is False
        print("✅ Règle anti-corruption respectée.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
