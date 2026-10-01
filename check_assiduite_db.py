"""check_assiduite_db.py - Test de bout en bout de l'Étape 5 sur la VRAIE base PostgreSQL.

Prérequis : seed_demo.py puis seed_assiduite.py exécutés ; variables DATABASE_URL, JWT_SECRET, QR_SECRET définies.
Vérifie : calcul du taux et blocage (dont le cas limite 85 % pile), parité Python/SQL du hash, verrou
inaltérable de la base (UPDATE/DELETE refusés), validation des QR (authentique, bloqué, falsifié), et
qu'une correction de présence APRÈS génération ne débloque jamais une convocation.
Lancement :  python check_assiduite_db.py
"""
import sys
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

import assiduite
import models as m
from config import get_settings
from database import SessionLocal

ATTENDU = {"Amani": (Decimal("100.00"), False), "Bamba": (Decimal("85.00"), False),
           "Coulibaly": (Decimal("80.00"), True), "Diallo": (Decimal("100.00"), False)}
ECHECS: list[str] = []


def verifier(condition: bool, libelle: str) -> None:
    print(("  ✓ " if condition else "  ✗ ") + libelle)
    if not condition:
        ECHECS.append(libelle)


def sqlstate(e: DBAPIError):
    return getattr(e.orig, "sqlstate", None) or getattr(e.orig, "pgcode", None)


def refuse_par_trigger(db, sql: str, params: dict) -> bool:
    """Vrai si la base refuse l'opération par une règle métier (RAISE EXCEPTION, SQLSTATE P0001)."""
    try:
        db.execute(text(sql), params)
        db.commit()
    except DBAPIError as e:
        db.rollback()
        return sqlstate(e) == "P0001"
    db.rollback()                      # l'opération a réussi : on annule ses effets, le test échouera
    return False


def main() -> None:
    db = SessionLocal()
    secret = get_settings().qr_secret
    session_id = db.scalar(text("SELECT id FROM sessions_examens WHERE code = 'DEMO-BEPC'"))
    if session_id is None:
        sys.exit("Session DEMO-BEPC introuvable : lancez seed_demo.py puis seed_assiduite.py.")
    eleves = {nom: (iid, roll) for iid, roll, nom in db.execute(text(
        "SELECT i.id, e.roll_number, e.nom FROM inscriptions i JOIN eleves e ON e.id = i.eleve_id "
        "WHERE e.prenoms = 'AssiduDemo'")).all()}
    if set(eleves) != set(ATTENDU):
        sys.exit("Élèves de démonstration incomplets : relancez seed_assiduite.py sur une base propre.")

    print("1. Génération des convocations (SQL) + contrôle d'intégrité Python")
    crees, anomalies = assiduite.generer_convocations_session(db, session_id)
    db.commit()
    verifier(not anomalies, f"aucune anomalie d'intégrité ({crees} convocation(s) créée(s) ce coup-ci)")

    print("2. Taux et blocage (seuil strict : 85 % pile est convoqué)")
    convocations = {}
    for nom, (iid, roll) in eleves.items():
        conv = db.scalar(m.Convocation.__table__.select().with_only_columns(m.Convocation.id)
                         .where(m.Convocation.session_id == session_id, m.Convocation.inscription_id == iid))
        convocations[nom] = db.get(m.Convocation, conv)
        taux, bloque = ATTENDU[nom]
        c = convocations[nom]
        verifier(c.taux_assiduite_fige == taux and c.bloque is bloque,
                 f"{nom:<10} taux {c.taux_assiduite_fige} % -> {'BLOQUÉ' if c.bloque else 'convoqué'}"
                 f" (attendu {taux} %, {'bloqué' if bloque else 'convoqué'})")

    print("3. Parité Python / SQL du message signé (diagnostic précis en cas d'écart)")
    for nom, (iid, roll) in eleves.items():
        c = convocations[nom]
        sql_message = db.scalar(text(
            "SELECT concat_ws('|', c.id::text, e.roll_number, c.session_id::text, c.taux_assiduite_fige::text, "
            "c.bloque::text, to_char(c.genere_le AT TIME ZONE 'UTC', :fmt)) FROM convocations_examens c "
            "JOIN inscriptions i ON i.id = c.inscription_id JOIN eleves e ON e.id = i.eleve_id WHERE c.id = :id"),
            {"fmt": 'YYYY-MM-DD"T"HH24:MI:SS.US', "id": c.id})
        py_message = assiduite.message_hash(c.id, roll, c.session_id, c.taux_assiduite_fige, c.bloque, c.genere_le)
        verifier(sql_message == py_message, f"{nom:<10} message identique" + ("" if sql_message == py_message
                 else f"\n      SQL    : {sql_message}\n      Python : {py_message}"))
        attendu = assiduite.calculer_hash_qr(secret, c.id, roll, c.session_id, c.taux_assiduite_fige, c.bloque, c.genere_le)
        verifier(assiduite.hash_identiques(attendu, c.hash_qr), f"{nom:<10} HMAC recalculé = HMAC de la base")

    print("4. Verrou inaltérable de la base")
    c = convocations["Coulibaly"]
    verifier(refuse_par_trigger(db, "UPDATE convocations_examens SET bloque = false WHERE id = :id", {"id": c.id}),
             "UPDATE bloque = false refusé")
    verifier(refuse_par_trigger(db, "UPDATE convocations_examens SET taux_assiduite_fige = 100 WHERE id = :id", {"id": c.id}),
             "UPDATE du taux refusé")
    verifier(refuse_par_trigger(db, "UPDATE convocations_examens SET hash_qr = repeat('a', 64) WHERE id = :id", {"id": c.id}),
             "UPDATE du hash refusé")
    verifier(refuse_par_trigger(db, "DELETE FROM convocations_examens WHERE id = :id", {"id": c.id}),
             "DELETE refusé")
    verifier(refuse_par_trigger(db, "TRUNCATE convocations_examens", {}), "TRUNCATE refusé")
    db.execute(text("UPDATE convocations_examens SET numero_table = 'T-001' WHERE id = :id"), {"id": c.id})
    db.commit()
    verifier(True, "champ opérationnel (numero_table) modifiable")
    db.refresh(c)
    verifier(c.bloque is True and c.taux_assiduite_fige == Decimal("80.00"), "Coulibaly toujours BLOQUÉ à 80.00 %")

    print("5. Validation des QR Codes")
    amani, bamba = convocations["Amani"], convocations["Bamba"]
    ok = assiduite.valider_qr(db, assiduite.payload_qr(bamba))
    verifier(ok.valide and ok.autorise_entree and ok.bloque is False, "Bamba (85 % pile) : QR authentique, entrée autorisée")
    bl = assiduite.valider_qr(db, assiduite.payload_qr(c))
    verifier(bl.valide and bl.bloque is True and not bl.autorise_entree and bl.raison == "CONVOCATION_BLOQUEE_ASSIDUITE",
             "Coulibaly : QR authentique mais entrée REFUSÉE")
    p = assiduite.payload_qr(amani)
    dernier = "0" if p[-1] != "0" else "1"
    verifier(not assiduite.valider_qr(db, p[:-1] + dernier).valide, "QR falsifié (1 caractère) refusé")
    verifier(assiduite.valider_qr(db, p[:-1] + dernier).raison == "QR_INVALIDE", "même réponse qu'un QR inconnu (pas d'oracle)")
    verifier(assiduite.valider_qr(db, "n'importe quoi").raison == "FORMAT_INVALIDE", "format invalide refusé")
    autre = assiduite.payload_qr(bamba).replace(str(bamba.id), str(amani.id))
    verifier(not assiduite.valider_qr(db, autre).valide, "hash d'un élève collé sur la convocation d'un autre : refusé")
    try:
        png = assiduite.generer_image_qr(p)
        verifier(png[:8] == b"\x89PNG\r\n\x1a\n", "image PNG du QR générée")
    except ImportError:
        verifier(False, "bibliothèque qrcode manquante : pip install 'qrcode[pil]'")

    print("6. Une correction APRÈS génération ne débloque jamais (immunité totale)")
    iid = eleves["Coulibaly"][0]
    ligne = db.execute(text(
        "SELECT p.id, p.date_seance FROM presences_eleves p JOIN seances_cours s ON s.id = p.seance_id "
        "AND s.date_seance = p.date_seance WHERE p.inscription_id = :i AND p.statut = 'ABSENT' "
        "AND s.statut = 'DISPENSE' ORDER BY p.date_seance LIMIT 1"), {"i": iid}).first()
    db.execute(text("UPDATE presences_eleves SET statut = CAST('PRESENT' AS statut_presence) "
                    "WHERE id = :id AND date_seance = :d"), {"id": ligne.id, "d": ligne.date_seance})
    db.commit()
    en_direct = assiduite.calculer_assiduite(db, iid)
    verifier(en_direct.taux == Decimal("85.00") and not en_direct.bloque,
             f"après correction, l'assiduité EN DIRECT de Coulibaly est {en_direct.taux} %")
    db.refresh(c)
    verifier(c.bloque is True and c.taux_assiduite_fige == Decimal("80.00"),
             "mais la convocation reste BLOQUÉE à 80.00 % (figée à la génération)")
    db.execute(text("UPDATE presences_eleves SET statut = CAST('ABSENT' AS statut_presence) "
                    "WHERE id = :id AND date_seance = :d"), {"id": ligne.id, "d": ligne.date_seance})
    db.commit()                                         # remise en l'état de la démonstration
    db.close()

    print()
    if ECHECS:
        print(f"ÉCHEC : {len(ECHECS)} contrôle(s) en erreur.")
        sys.exit(1)
    print("OK : l'Étape 5 se comporte comme prévu sur la base réelle.")


if __name__ == "__main__":
    main()
