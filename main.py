import os
from flask import Flask, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

from database import engine, SessionLocal, Base
from models import Eleve, StatutAssiduiteEnum

# Charger les variables d'environnement
load_dotenv()

# Initialisation de l'application Flask
app = Flask(__name__)

# Création automatique des tables dans la base de données au démarrage
Base.metadata.create_all(bind=engine)

def get_enum_value(val):
    if hasattr(val, "value"):
        return val.value
    return val

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "app": "SigecEdu API Backend",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "health_check": "GET /health",
            "lister_eleves": "GET /api/eleves",
            "recuperer_eleve": "GET /api/eleves/<id>",
            "creer_eleve": "POST /api/eleves",
            "modifier_eleve": "PUT /api/eleves/<id>",
            "supprimer_eleve": "DELETE /api/eleves/<id>"
        }
    }), 200

@app.route("/health", methods=["GET"])
def health_check():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return jsonify({
            "status": "success",
            "message": "API SigecEdu opérationnelle et connectée à la base de données !"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Échec critique de la base de données : {str(e)}"
        }), 500
    finally:
        db.close()

@app.route("/api/eleves", methods=["GET"])
def lister_eleves():
    db = SessionLocal()
    try:
        eleves = db.query(Eleve).all()
        resultat = [
            {
                "id": e.id,
                "matricule": e.matricule,
                "nom": e.nom,
                "prenoms": e.prenoms,
                "taux_assiduite": e.taux_assiduite,
                "statut_assiduite": get_enum_value(e.statut_assiduite),
                "eligible_examen": e.eligible_examen
            }
            for e in eleves
        ]
        return jsonify({"status": "success", "data": resultat}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

@app.route("/api/eleves/<int:eleve_id>", methods=["GET"])
def recuperer_eleve(eleve_id):
    db = SessionLocal()
    try:
        eleve = db.query(Eleve).filter(Eleve.id == eleve_id).first()
        if not eleve:
            return jsonify({"status": "error", "message": "Élève introuvable"}), 404
        
        return jsonify({
            "status": "success",
            "data": {
                "id": eleve.id,
                "matricule": eleve.matricule,
                "nom": eleve.nom,
                "prenoms": eleve.prenoms,
                "taux_assiduite": eleve.taux_assiduite,
                "statut_assiduite": get_enum_value(eleve.statut_assiduite),
                "eligible_examen": eleve.eligible_examen
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

@app.route("/api/eleves", methods=["POST"])
def creer_eleve():
    donnees = request.get_json()
    if not donnees:
        return jsonify({"status": "error", "message": "Aucune donnée fournie"}), 400

    for champ in ["matricule", "nom", "prenoms"]:
        if champ not in donnees or not str(donnees[champ]).strip():
            return jsonify({"status": "error", "message": f"Le champ '{champ}' est obligatoire."}), 400

    db = SessionLocal()
    try:
        statut = StatutAssiduiteEnum.REGULIER
        if "statut_assiduite" in donnees:
            try:
                statut = StatutAssiduiteEnum(donnees["statut_assiduite"])
            except ValueError:
                return jsonify({"status": "error", "message": "Statut d'assiduité invalide."}), 422

        nouvel_eleve = Eleve(
            matricule=donnees["matricule"].strip().upper(),
            nom=donnees["nom"].strip().upper(),
            prenoms=donnees["prenoms"].strip().title(),
            taux_assiduite=float(donnees.get("taux_assiduite", 100.0)),
            statut_assiduite=statut,
            eligible_examen=bool(donnees.get("eligible_examen", True))
        )
        
        db.add(nouvel_eleve)
        db.commit()
        db.refresh(nouvel_eleve)
        
        return jsonify({
            "status": "success",
            "message": "Élève créé avec succès",
            "data": {"id": nouvel_eleve.id, "matricule": nouvel_eleve.matricule}
        }), 201

    except IntegrityError:
        db.rollback()
        return jsonify({"status": "error", "message": "Un élève avec ce matricule existe déjà."}), 409
    except ValueError:
        db.rollback()
        return jsonify({"status": "error", "message": "Type de donnée invalide."}), 422
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

@app.route("/api/eleves/<int:eleve_id>", methods=["PUT"])
def modifier_eleve(eleve_id):
    donnees = request.get_json()
    if not donnees:
        return jsonify({"status": "error", "message": "Aucune donnée fournie pour la mise à jour."}), 400

    db = SessionLocal()
    try:
        eleve = db.query(Eleve).filter(Eleve.id == eleve_id).first()
        if not eleve:
            return jsonify({"status": "error", "message": "Élève introuvable"}), 404

        if "matricule" in donnees:
            eleve.matricule = donnees["matricule"].strip().upper()
        if "nom" in donnees:
            eleve.nom = donnees["nom"].strip().upper()
        if "prenoms" in donnees:
            eleve.prenoms = donnees["prenoms"].strip().title()
        if "taux_assiduite" in donnees:
            eleve.taux_assiduite = float(donnees["taux_assiduite"])
        if "eligible_examen" in donnees:
            eleve.eligible_examen = bool(donnees["eligible_examen"])
        if "statut_assiduite" in donnees:
            try:
                eleve.statut_assiduite = StatutAssiduiteEnum(donnees["statut_assiduite"])
            except ValueError:
                return jsonify({"status": "error", "message": "Statut d'assiduité invalide."}), 422

        db.commit()
        return jsonify({"status": "success", "message": "Informations de l'élève mises à jour avec succès"}), 200

    except IntegrityError:
        db.rollback()
        return jsonify({"status": "error", "message": "Ce matricule est déjà utilisé par un autre élève."}), 409
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

@app.route("/api/eleves/<int:eleve_id>", methods=["DELETE"])
def supprimer_eleve(eleve_id):
    db = SessionLocal()
    try:
        eleve = db.query(Eleve).filter(Eleve.id == eleve_id).first()
        if not eleve:
            return jsonify({"status": "error", "message": "Élève introuvable"}), 404

        db.delete(eleve)
        db.commit()
        return jsonify({"status": "success", "message": f"L'élève avec l'ID {eleve_id} a été supprimé."}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
