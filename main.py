"""main.py - Routes FastAPI.

Lancement :  uvicorn main:app --host 0.0.0.0 --port 8000
Variables requises : DATABASE_URL, JWT_SECRET (>= 32 car.), QR_SECRET (>= 32 car., différent).

Choix de conception :
  * Aucune route ne modifie le blocage d'une convocation : il n'existe pas d'endpoint de
    déblocage, et la base (trigger) le refuserait de toute façon.
  * Rôles en liste blanche par route ; périmètre (établissement / structure) vérifié dans crud.py.
  * Les endpoints sont synchrones (`def`) : FastAPI les exécute dans son pool de threads,
    adapté à SQLAlchemy sync + psycopg.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

import assiduite
import crud
import models as m
import schemas as s
import security
from crud import ErreurMetier
from database import SessionLocal
from enums import RoleUtilisateur as R, StatutRetenue
from security import Claims, exiger_roles

app = FastAPI(title="Système éducatif - Côte d'Ivoire", version="0.2.0")


@app.exception_handler(ErreurMetier)
async def _erreur_metier(_: Request, exc: ErreurMetier):
    return JSONResponse(status_code=exc.statut_http, content={"code": exc.code, "detail": exc.message})


# ---------------------------------------------------------------------------
# Dépendances base de données
# ---------------------------------------------------------------------------
def db_anonyme():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_authentifiee(claims: Claims = Depends(security.get_claims)):
    """Session attribuée à l'utilisateur du jeton (audit) ; le compte doit être encore actif,
    ce qui rend la désactivation d'un compte immédiate malgré un jeton encore valide."""
    db = SessionLocal()
    db.info["user_id"] = str(claims.sub)
    try:
        u = db.get(m.Utilisateur, claims.sub)
        if u is None or not u.actif or u.role != claims.role:
            raise ErreurMetier("Session invalide", 401, "AUTH")
        yield db
    finally:
        db.close()


DB = Annotated[Session, Depends(db_authentifiee)]
DBAnon = Annotated[Session, Depends(db_anonyme)]


def _roles(*roles: R):
    return Depends(exiger_roles(*roles))


# ---------------------------------------------------------------------------
# Santé & authentification
# ---------------------------------------------------------------------------
@app.get("/sante", tags=["système"])
def sante(db: DBAnon):
    """Sonde utilisée par les clients hors ligne pour détecter le retour du réseau."""
    db.execute(text("SELECT 1"))
    return {"statut": "ok"}


@app.post("/auth/login", response_model=s.TokenOut, tags=["auth"])
def login(data: s.LoginIn, db: DBAnon):
    utilisateur = crud.authentifier(db, data.identifiant, data.mot_de_passe)
    jeton, duree = security.creer_jeton(utilisateur)
    return s.TokenOut(access_token=jeton, expires_in=duree)


@app.post("/utilisateurs", response_model=s.UtilisateurOut, status_code=201, tags=["référentiel"])
def creer_utilisateur(data: s.UtilisateurCreate, db: DB, _: Claims = _roles(R.ADMIN)):
    return crud.creer_utilisateur(db, data)


# ---------------------------------------------------------------------------
# Référentiel
# ---------------------------------------------------------------------------
@app.post("/etablissements", response_model=s.EtablissementOut, status_code=201, tags=["référentiel"])
def creer_etablissement(data: s.EtablissementCreate, db: DB, _: Claims = _roles(R.ADMIN)):
    return crud.creer_etablissement(db, data)


@app.post("/professeurs", response_model=s.ProfesseurOut, status_code=201, tags=["référentiel"])
def creer_professeur(data: s.ProfesseurCreate, db: DB, claims: Claims = _roles(R.ADMIN, R.DIRECTEUR)):
    return crud.creer_professeur(db, data, claims)


@app.post("/eleves", response_model=s.EleveOut, status_code=201, tags=["référentiel"])
def creer_eleve(data: s.EleveCreate, db: DB, claims: Claims = _roles(R.ADMIN, R.DIRECTEUR)):
    return crud.creer_eleve(db, data, claims)


# ---------------------------------------------------------------------------
# Service fait : séances, remplacements, pointage des professeurs
# ---------------------------------------------------------------------------
@app.get("/professeurs/{professeur_id}/seances", response_model=list[s.SeanceOut], tags=["service fait"])
def seances_du_jour(professeur_id: uuid.UUID, db: DB, jour: date = Query(default_factory=date.today),
                    claims: Claims = _roles(R.ADMIN, R.DIRECTEUR, R.PROFESSEUR, R.INSPECTEUR)):
    return crud.seances_du_jour(db, professeur_id, jour, claims)


@app.post("/remplacements", response_model=s.RemplacementOut, status_code=201, tags=["service fait"])
def declarer_remplacement(data: s.RemplacementCreate, db: DB,
                          claims: Claims = _roles(R.ADMIN, R.DIRECTEUR, R.PROFESSEUR)):
    """Le préavis de 24 h est calculé par le serveur à la réception : `conforme_preavis` fait foi."""
    return crud.declarer_remplacement(db, data, claims)


@app.post("/pointages", response_model=s.PointageResultat, tags=["service fait"])
def pointer(data: s.PointageCreate, response: Response, db: DB, claims: Claims = _roles(R.ADMIN, R.DIRECTEUR)):
    """Pointage biométrique heure par heure. Les terminaux s'authentifient avec un compte DIRECTEUR
    (un rôle TERMINAL dédié est recommandé en production). Idempotent."""
    pointage, deja, seance = crud.enregistrer_pointage(db, data, claims)
    response.status_code = 200 if deja else 201
    return s.PointageResultat(pointage=s.PointageOut.model_validate(pointage),
                              deja_enregistre=deja, statut_seance=seance.statut)


@app.post("/maintenance/evaluer-seances", response_model=s.EvaluationResultat, tags=["service fait"])
def evaluer_seances(db: DB, _: Claims = _roles(R.ADMIN)):
    """Détection automatique des cours non dispensés + retenues. À appeler toutes les heures
    (cron / planificateur) avec un compte de service ADMIN."""
    return crud.evaluer_et_generer_retenues(db)


# ---------------------------------------------------------------------------
# Impact salarial (avec contestation)
# ---------------------------------------------------------------------------
@app.get("/salaires/retenues", response_model=list[s.RetenueOut], tags=["salaires"])
def lister_retenues(db: DB, statut: StatutRetenue | None = None, professeur_id: uuid.UUID | None = None,
                    claims: Claims = _roles(R.ADMIN, R.DIRECTEUR, R.PROFESSEUR)):
    """Filtrer `statut=VALIDEE` donne le flux exportable vers la paie."""
    return crud.lister_retenues(db, claims, statut, professeur_id)


@app.post("/salaires/retenues/{retenue_id}/contester", response_model=s.RetenueOut, tags=["salaires"])
def contester(retenue_id: uuid.UUID, data: s.ContestationIn, db: DB, claims: Claims = _roles(R.PROFESSEUR)):
    return crud.contester_retenue(db, retenue_id, data.motif, claims)


@app.post("/salaires/retenues/{retenue_id}/trancher", response_model=s.RetenueOut, tags=["salaires"])
def trancher(retenue_id: uuid.UUID, data: s.DecisionRetenueIn, db: DB, claims: Claims = _roles(R.ADMIN, R.DIRECTEUR)):
    return crud.trancher_retenue(db, retenue_id, data, claims)


# ---------------------------------------------------------------------------
# Appel élèves hors ligne
# ---------------------------------------------------------------------------
@app.get("/seances/{seance_id}/liste-appel", response_model=s.ListeAppelOut, tags=["appel"])
def liste_appel(seance_id: uuid.UUID, db: DB, claims: Claims = _roles(R.ADMIN, R.DIRECTEUR, R.PROFESSEUR)):
    """Liste de classe téléchargée par l'appareil AVANT la coupure réseau."""
    return crud.liste_appel(db, seance_id, claims)


@app.post("/sync/appels", response_model=s.AppelSyncResponse, tags=["appel"])
def sync_appels(data: s.AppelSyncRequest, db: DB, claims: Claims = _roles(R.ADMIN, R.DIRECTEUR, R.PROFESSEUR)):
    return crud.enregistrer_appels_sync(db, data, claims)


# ---------------------------------------------------------------------------
# Assiduité, convocations, QR Codes
# ---------------------------------------------------------------------------
@app.get("/inscriptions/{inscription_id}/assiduite", response_model=s.AssiduiteOut, tags=["assiduité"])
def assiduite_eleve(inscription_id: uuid.UUID, db: DB,
                    claims: Claims = _roles(R.ADMIN, R.DIRECTEUR, R.INSPECTEUR)):
    return crud.assiduite_inscription(db, inscription_id, claims)


@app.post("/convocations", response_model=s.ConvocationOut, status_code=201, tags=["examens"])
def creer_convocation(data: s.ConvocationCreate, response: Response, db: DB,
                      claims: Claims = _roles(R.ADMIN, R.DIRECTEUR)):
    """Calcule et FIGE le taux d'assiduité. Sous 85 %, `bloque` = true pour toujours."""
    conv, creee = crud.creer_convocation(db, data, claims)
    response.status_code = 201 if creee else 200
    return conv


@app.post("/examens/{session_id}/convocations", response_model=s.GenerationSessionOut, tags=["examens"])
def generer_session(session_id: uuid.UUID, db: DB, _: Claims = _roles(R.ADMIN)):
    """Génération en masse pour tous les élèves du niveau concerné, puis contrôle d'intégrité."""
    return crud.generer_convocations_session(db, session_id)


@app.get("/convocations/{convocation_id}/qr.png", tags=["examens"],
         responses={200: {"content": {"image/png": {}}}, 403: {"description": "Convocation bloquée"}})
def qr_png(convocation_id: uuid.UUID, db: DB, claims: Claims = _roles(R.ADMIN, R.DIRECTEUR)):
    png = crud.image_qr_convocation(db, convocation_id, claims)
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "no-store"})


@app.post("/qr/verifier", response_model=s.QRVerifierOut, tags=["examens"])
def verifier_qr(data: s.QRVerifierIn, db: DB, _: Claims = _roles(R.ADMIN, R.DIRECTEUR, R.INSPECTEUR)):
    """Contrôle à l'entrée de la salle : `autorise_entree` est vrai uniquement pour un QR
    authentique dont la convocation n'est pas bloquée."""
    r = assiduite.valider_qr(db, data.payload)
    return s.QRVerifierOut(valide=r.valide, bloque=r.bloque, autorise_entree=r.autorise_entree,
                           roll_number=r.roll_number, nom=r.nom, prenoms=r.prenoms, raison=r.raison)
