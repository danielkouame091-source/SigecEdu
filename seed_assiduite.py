"""seed_assiduite.py - Données DE DÉMONSTRATION pour tester l'Étape 5 (seuil de 85 % et QR Codes).
NE PAS lancer en production. À lancer APRÈS seed_demo.py (même base).

Crée dans la classe '3EME A' du lycée de démonstration, 4 élèves et 21 séances passées :
  * 20 séances DISPENSE (comptées) + 1 séance NON_DISPENSE (tous absents : NE DOIT PAS compter) ;
  * Amani     20/20 présent  -> 100.00 %  -> convoqué
  * Bamba     17/20 présent  ->  85.00 %  -> convoqué (le seuil est STRICT : 85 % pile passe)
  * Coulibaly 16/20 présent  ->  80.00 %  -> BLOQUÉ
  * Diallo    20/20 présent  -> 100.00 %  -> convoqué (son absence du cours non dispensé ne compte pas)
et une session d'examen 'DEMO-BEPC' (niveau 3EME).

Lancement :  python seed_assiduite.py
"""
import json
import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import text

from database import SessionLocal

PRENOM_MARQUEUR = "AssiduDemo"
ELEVES = (("Amani", 0), ("Bamba", 3), ("Coulibaly", 4), ("Diallo", 0))      # (nom, absences sur les 20 séances comptées)
ATTENDU = {"Amani": "100.00", "Bamba": "85.00", "Coulibaly": "80.00", "Diallo": "100.00"}


def main() -> None:
    db = SessionLocal()
    try:
        classe = db.execute(text(
            "SELECT c.id, c.annee_id FROM classes c JOIN etablissements e ON e.id = c.etablissement_id "
            "WHERE e.code_etablissement = 'DEMO-LYC-001' AND c.libelle = '3EME A'")).first()
        if classe is None:
            sys.exit("Lancez d'abord seed_demo.py (lycée et classe de démonstration introuvables).")
        if db.scalar(text("SELECT 1 FROM eleves WHERE prenoms = :p"), {"p": PRENOM_MARQUEUR}):
            sys.exit("Les données d'assiduité de démonstration existent déjà.")
        prof = db.scalar(text("SELECT id FROM professeurs WHERE matricule_fonction_publique = 'DEMO-001A'"))
        matiere = db.scalar(text("SELECT id FROM matieres WHERE code LIKE 'DEMO-MATH-%' LIMIT 1"))
        if prof is None or matiere is None:
            sys.exit("Professeur ou matière de démonstration introuvables : relancez seed_demo.py sur une base vide.")

        # Créneau fixe (lundi 14h-15h) : sert de support aux 21 séances passées
        emploi = uuid.uuid4()
        db.execute(text("INSERT INTO emploi_du_temps (id, classe_id, matiere_id, professeur_id, jour_semaine, "
                        "heure_debut, heure_fin) VALUES (:id, :c, :m, :p, 1, :d, :f)"),
                   {"id": emploi, "c": classe.id, "m": matiere, "p": prof, "d": time(14, 0), "f": time(15, 0)})

        seances = []                                   # (id, date, comptee) ; la plus ancienne est NON_DISPENSE
        for i in range(21):
            jour = date.today() - timedelta(days=i + 1)
            comptee = i < 20
            sid = uuid.uuid4()
            debut = datetime.combine(jour, time(14, 0), tzinfo=timezone.utc)
            db.execute(text(
                "INSERT INTO seances_cours (id, emploi_id, classe_id, professeur_prevu_id, date_seance, debut, fin, "
                "statut, professeur_effectif_id) VALUES (:id, :e, :c, :p, :j, :d, :f, CAST(:s AS statut_seance), :pe)"),
                {"id": sid, "e": emploi, "c": classe.id, "p": prof, "j": jour, "d": debut,
                 "f": debut + timedelta(hours=1), "s": "DISPENSE" if comptee else "NON_DISPENSE",
                 "pe": prof if comptee else None})
            seances.append((sid, jour, comptee, debut))

        sortie = {}
        for rang, (nom, nb_absences) in enumerate(ELEVES, start=1):
            eleve, insc = uuid.uuid4(), uuid.uuid4()
            db.execute(text("INSERT INTO eleves (id, nom, prenoms, date_naissance, sexe) "
                            "VALUES (:id, :n, :p, :d, 'M')"),
                       {"id": eleve, "n": nom, "p": PRENOM_MARQUEUR, "d": date(2011, 6, 1)})
            db.execute(text("INSERT INTO inscriptions (id, eleve_id, classe_id, annee_id) VALUES (:i, :e, :c, :a)"),
                       {"i": insc, "e": eleve, "c": classe.id, "a": classe.annee_id})
            for index, (sid, jour, comptee, debut) in enumerate(seances):
                absent = (not comptee) or index < nb_absences            # absences placées sur les premières séances
                db.execute(text(
                    "INSERT INTO presences_eleves (id, seance_id, date_seance, inscription_id, ordre_appel, statut, "
                    "horodatage) VALUES (:id, :s, :j, :i, :o, CAST(:st AS statut_presence), :h)"),
                    {"id": uuid.uuid4(), "s": sid, "j": jour, "i": insc, "o": rang,
                     "st": "ABSENT" if absent else "PRESENT", "h": debut + timedelta(minutes=5)})
            roll = db.scalar(text("SELECT roll_number FROM eleves WHERE id = :e"), {"e": eleve})
            sortie[nom] = {"roll_number": roll, "inscription_id": str(insc), "taux_attendu": ATTENDU[nom],
                           "bloque_attendu": nom == "Coulibaly"}

        session_id = uuid.uuid4()
        db.execute(text("INSERT INTO sessions_examens (id, annee_id, code, libelle, niveau_concerne, date_debut, date_fin) "
                        "VALUES (:id, :a, 'DEMO-BEPC', 'BEPC (démonstration)', '3EME', :d, :f)"),
                   {"id": session_id, "a": classe.annee_id,
                    "d": date.today() + timedelta(days=60), "f": date.today() + timedelta(days=65)})
        db.execute(text("SELECT recalculer_assiduite(p_classe => CAST(:c AS uuid))"), {"c": str(classe.id)})
        db.commit()
    finally:
        db.close()
    print(json.dumps({"session_id": str(session_id), "eleves": sortie}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
