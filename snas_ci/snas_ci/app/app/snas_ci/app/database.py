"""Configuration SQLAlchemy."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


# Pour SQLite : autorise le multi-thread (FastAPI l'utilise)
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,   # Affiche les requêtes SQL en mode debug
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Classe mère dont héritent TOUS les modèles."""
    pass


def get_db():
    """
    Dépendance FastAPI : fournit une session par requête HTTP
    et la ferme automatiquement à la fin.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
