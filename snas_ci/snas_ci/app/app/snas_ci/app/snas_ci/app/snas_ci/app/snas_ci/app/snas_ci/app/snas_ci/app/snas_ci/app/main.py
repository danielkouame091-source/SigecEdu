"""Point d'entrée FastAPI du système SNAS-CI."""
from fastapi import FastAPI

from app.config import settings
from app.routers import auth


app = FastAPI(
    title="SNAS-CI API",
    description="Système National d'Assiduité Scolaire - Côte d'Ivoire",
    version=settings.APP_VERSION,
)


@app.get("/", tags=["Santé"])
def racine():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "OK",
        "seuil_assiduite": settings.SEUIL_ASSIDUITE,
        "delai_justificatif_heures": settings.DELAI_JUSTIFICATIF_HEURES,
    }


@app.get("/health", tags=["Santé"])
def health():
    return {"status": "healthy"}


app.include_router(auth.router)
