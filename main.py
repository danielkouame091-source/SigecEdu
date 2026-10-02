from flask import Flask, jsonify
from sqlalchemy import text
from database import SessionLocal

# Initialisation de l'application Flask
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    """Route racine pour indiquer que l'API est en ligne et lister les points d'accès."""
    return jsonify({
        "app": "SigecEdu API Backend",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "health_check": "/health",
            "eleves": "/api/eleves"
        }
    }), 200

@app.route("/health", methods=["GET"])
def health_check():
    """Vérifie l'intégrité de l'API et la bonne connexion au serveur de base de données."""
    db = None
    try:
        db = SessionLocal()
        # Test de la connexion avec SQLAlchemy 2.0
        db.execute(text("SELECT 1"))
        return jsonify({
            "status": "success",
            "message": "API SigecEdu opérationnelle et connectée à la base de données !"
        }), 200
    except Exception as e:
        # Capture précise de l'erreur sans crasher brutalement le serveur (Code 500 contrôlé)
        return jsonify({
            "status": "error",
            "message": f"Échec critique de la base de données : {str(e)}"
        }), 500
    finally:
        if db:
            db.close()

@app.route("/api/eleves", methods=["GET"])
def lister_eleves():
    """Récupère et sérialise la liste de tous les élèves enregistrés."""
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
        return jsonify({
            "status": "success",
            "count": len(resultat),
            "data": resultat
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erreur lors de la récupération des élèves : {str(e)}"
        }), 500
    finally:
        db.close()

if __name__ == "__main__":
    # Exécution locale pour le développement (Gunicorn prend le relais en production sur Render)
    app.run(host="0.0.0.0", port=5001, debug=True)
