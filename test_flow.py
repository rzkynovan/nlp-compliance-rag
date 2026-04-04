import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    resp = requests.get(f"{BASE_URL}/health")
    print(f"Health: {resp.status_code} - {resp.json()}")
    return resp.status_code == 200

def test_audit(clause_text):
    payload = {
        "clause": clause_text,
        "regulator": "all",
        "top_k": 5
    }
    resp = requests.post(f"{BASE_URL}/audit/analyze", json=payload)
    print(f"Audit Result: {json.dumps(resp.json(), indent=2)}")
    return resp.json()

def test_usage():
    resp = requests.get(f"{BASE_URL}/usage")
    print(f"Usage Stats: {json.dumps(resp.json(), indent=2)}")

if __name__ == "__main__":
    print("=== Testing Health ===")
    test_health()
    
    print("\n=== Testing Audit ===")
    result = test_audit("Saldo maksimal e-wallet untuk akun unverified adalah Rp 2.000.000")
    
    print("\n=== Testing Usage ===")
    test_usage()