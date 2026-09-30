"""Script d'initialisation de la base de données."""
from app.database import Base, engine
from app import models  # IMPORTANT : importe les modèles pour qu'ils soient enregistrés
from app.config import settings


def init_database():
    print("=" * 60)
    print(f"  Initialisation de la base : {settings.DATABASE_URL}")
    print("=" * 60)

    # Crée toutes les tables définies dans models.py
    Base.metadata.create_all(bind=engine)

    # Liste les tables créées
    tables = list(Base.metadata.tables.keys())
    print(f"\n✅ {len(tables)} tables créées avec succès :\n")
    for t in sorted(tables):
        print(f"   • {t}")

    print("\n🎉 Base de données prête !\n")


if __name__ == "__main__":
    init_database()
