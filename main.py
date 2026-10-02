from flask import Flask, jsonify
from sqlalchemy import text
from database import SessionLocal

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    """Vérifie l'état de l'API et capture précisément l'erreur DB si elle existe."""
    db = None
    try:
        db = SessionLocal()
        # Test de la connexion avec SQLAlchemy 2.0
        db.execute(text("SELECT 1"))
        return jsonify({
            "status": "success",
            "message": "API Education CI opérationnelle et connectée à PostgreSQL !"
        }), 200
    except Exception as e:
        # On retourne un JSON propre avec l'erreur exacte au lieu de crasher en 500 brut
        return jsonify({
            "status": "error",
            "message": f"Échec de la base de données : {str(e)}"
        }), 500
    finally:
        if db:
            db.close()

@app.route("/api/eleves", methods=["GET"])
def lister_eleves():
    """Récupère la liste de tous les élèves."""
    db = SessionLocal()
    try:
        from models import Eleve
        eleves = db.query(Eleve).all()
        resultat = [
            {
                "id": e.id,
                "matricule": e.matricule,
                "nom": e.nom,
                "prenoms": e.prenoms,
                "taux_assiduite": e.taux_assiduite,
                "statut_assiduite": e.statut_assiduite.value if hasattr(e.statut_assiduite, "value") else e.statut_assiduite,
                "eligible_examen": e.eligible_examen
            }
            for e in eleves
        ]
        return jsonify({"status": "success", "data": resultat}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
