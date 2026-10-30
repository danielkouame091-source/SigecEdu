"""Quick smoke test: starts the API on port 5001, calls two endpoints, then stops it.
Usage:  python test_api.py"""
import json
import os
import subprocess
import sys
import time
import urllib.request

print("🚀 Starting the test Flask server...")
env = dict(os.environ, PORT="5001")
process = subprocess.Popen([sys.executable, "main.py"], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)  # give Flask time to start

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

    print("\n✅ All tests passed!")

except Exception as e:
    print(f"\n❌ Error during the tests: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    print("\n🛑 Stopping the server...")
    process.terminate()
    process.wait()
