"""Create the first administrator account.
Usage:  python creer_admin.py admin@example.com   (the password is asked in the terminal, never stored in clear)."""
import sys
import getpass
from database import SessionLocal
from models import Utilisateur
from werkzeug.security import generate_password_hash

def creer_admin(email):
    db = SessionLocal()
    try:
        # Stop if this e-mail is already registered
        existing = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        if existing:
            print(f"Error: a user with the e-mail {email} already exists.")
            return

        password = getpass.getpass("Administrator password (12 characters minimum): ")
        if len(password) < 12:
            print("Error: the password must contain at least 12 characters.")
            return

        hashed_password = generate_password_hash(password)
        
        admin_user = Utilisateur(
            email=email,
            hashed_password=hashed_password,
            role="ADMIN",
            nom="Admin",
            prenoms="System",
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        print(f"Success: administrator {email} created!")
    except Exception as e:
        db.rollback()
        print(f"Error while creating the account: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python creer_admin.py <email>")
        sys.exit(1)
    creer_admin(sys.argv[1])
