#!/usr/bin/env python3
import requests
import time
import sys

API = "http://localhost:8000"
COMPOUNDS = [
    {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O", "tags": ["NSAID"]},
    {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", "tags": ["NSAID"]},
    {"name": "Caffeine", "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "tags": ["stimulant"]},
]

print("Waiting for API...")
for i in range(30):
    try:
        if requests.get(f"{API}/health", timeout=2).status_code == 200:
            print("✅ API ready")
            break
    except:
        pass
    time.sleep(1)
else:
    print("❌ API timeout")
    sys.exit(1)

print("\nLoading compounds...")
for c in COMPOUNDS:
    try:
        r = requests.post(f"{API}/compounds/", json=c)
        print(f"  {'✅' if r.status_code == 200 else '❌'} {c['name']}")
    except Exception as e:
        print(f"  ❌ {c['name']}: {e}")

print("\n✅ Done! Visit http://localhost:3000")
