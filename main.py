"""SigecEdu API: a small Flask web service to manage students and their attendance."""
import os
from flask import Flask, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

from database import engine, SessionLocal, Base
from enums import StatutAssiduite
from models import Eleve

# Load environment variables
load_dotenv()

# Create the Flask application
app = Flask(__name__)

# Create the database tables automatically at start-up (nothing happens if they already exist)
Base.metadata.create_all(bind=engine)

def get_enum_value(val):
    """Return the readable text of an enumeration value (for example "Regular")."""
    if hasattr(val, "value"):
        return val.value
    return val

@app.route("/", methods=["GET"])
def index():
    """API home page: name, status and list of available endpoints."""
    return jsonify({
        "app": "SigecEdu API Backend",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "health_check": "GET /health",
            "list_students": "GET /api/eleves",
            "get_student": "GET /api/eleves/<id>",
            "create_student": "POST /api/eleves",
            "update_student": "PUT /api/eleves/<id>",
            "delete_student": "DELETE /api/eleves/<id>"
        }
    }), 200

@app.route("/health", methods=["GET"])
def health_check():
    """Check that the API is alive and can reach the database."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return jsonify({
            "status": "success",
            "message": "SigecEdu API is running and connected to the database!"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Critical database failure: {str(e)}"
        }), 500
    finally:
        db.close()

@app.route("/api/eleves", methods=["GET"])
def lister_eleves():
    """Return all students."""
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
    """Return one student by its database id."""
    db = SessionLocal()
    try:
        eleve = db.query(Eleve).filter(Eleve.id == eleve_id).first()
        if not eleve:
            return jsonify({"status": "error", "message": "Student not found"}), 404
        
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
    """Create a student. Required JSON fields: matricule, nom, prenoms."""
    donnees = request.get_json()
    if not donnees:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    for champ in ["matricule", "nom", "prenoms"]:
        if champ not in donnees or not str(donnees[champ]).strip():
            return jsonify({"status": "error", "message": f"The field '{champ}' is required."}), 400

    db = SessionLocal()
    try:
        statut = StatutAssiduite.REGULIER
        if "statut_assiduite" in donnees:
            try:
                statut = StatutAssiduite(donnees["statut_assiduite"])
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid attendance status. Allowed values: Regular, Irregular, Absent, Excluded."}), 422

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
            "message": "Student created successfully",
            "data": {"id": nouvel_eleve.id, "matricule": nouvel_eleve.matricule}
        }), 201

    except IntegrityError:
        db.rollback()
        return jsonify({"status": "error", "message": "A student with this ID (matricule) already exists."}), 409
    except ValueError:
        db.rollback()
        return jsonify({"status": "error", "message": "Invalid data type."}), 422
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

@app.route("/api/eleves/<int:eleve_id>", methods=["PUT"])
def modifier_eleve(eleve_id):
    """Update the fields sent in the JSON body (the others stay unchanged)."""
    donnees = request.get_json()
    if not donnees:
        return jsonify({"status": "error", "message": "No data provided for the update."}), 400

    db = SessionLocal()
    try:
        eleve = db.query(Eleve).filter(Eleve.id == eleve_id).first()
        if not eleve:
            return jsonify({"status": "error", "message": "Student not found"}), 404

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
                eleve.statut_assiduite = StatutAssiduite(donnees["statut_assiduite"])
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid attendance status. Allowed values: Regular, Irregular, Absent, Excluded."}), 422

        db.commit()
        return jsonify({"status": "success", "message": "Student information updated successfully"}), 200

    except IntegrityError:
        db.rollback()
        return jsonify({"status": "error", "message": "This ID (matricule) is already used by another student."}), 409
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

@app.route("/api/eleves/<int:eleve_id>", methods=["DELETE"])
def supprimer_eleve(eleve_id):
    """Delete a student."""
    db = SessionLocal()
    try:
        eleve = db.query(Eleve).filter(Eleve.id == eleve_id).first()
        if not eleve:
            return jsonify({"status": "error", "message": "Student not found"}), 404

        db.delete(eleve)
        db.commit()
        return jsonify({"status": "success", "message": f"The student with ID {eleve_id} has been deleted."}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=debug_mode)
