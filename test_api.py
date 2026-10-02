import subprocess
import time
import urllib.request
import json
import sys

print("🚀 Démarrage du serveur Flask de test...")
process = subprocess.Popen(["python", "main.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3) # Laisser le temps à Flask de s'initialiser

base_url = "http://127.0.0.1:5001"

try:
    print("\n--- 1. TEST /health ---")
    with urllib.request.urlopen(f"{base_url}/health") as response:
        data = json.loads(response.read().decode())
        print(json.dumps(data, indent=4, ensure_ascii=False))

    print("\n--- 2. TEST /api/eleves ---")
    with urllib.request.urlopen(f"{base_url}/api/eleves") as response:
        data = json.loads(response.read().decode())
        print(json.dumps(data, indent=4, ensure_ascii=False))
        
    print("\n✅ Tous les tests ont réussi avec succès !")

except Exception as e:
    print(f"\n❌ Erreur lors des tests : {e}", file=sys.stderr)
finally:
    print("\n🛑 Arrêt propre du serveur...")
    process.terminate()
    process.wait()
