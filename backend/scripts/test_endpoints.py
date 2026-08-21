import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

def main():
    client = TestClient(app)
    print("--- VERIFYING FASTAPI API ENDPOINTS ---")

    endpoints = [
        ("GET /", "/"),
        ("GET /health", "/health"),
        ("GET /api/v1/transactions", "/api/v1/transactions"),
        ("GET /api/v1/revenue-risk", "/api/v1/revenue-risk"),
        ("GET /api/v1/revenue-risk/summary", "/api/v1/revenue-risk/summary"),
        ("GET /api/v1/recovery-opportunities", "/api/v1/recovery-opportunities"),
        ("GET /api/v1/recovery-opportunities/summary", "/api/v1/recovery-opportunities/summary"),
        ("GET /api/v1/analytics/overview", "/api/v1/analytics/overview"),
        ("GET /api/v1/evaluation/latest", "/api/v1/evaluation/latest"),
        ("GET /api/v1/evaluation/metrics", "/api/v1/evaluation/metrics")
    ]

    for name, path in endpoints:
        resp = client.get(path)
        print(f"[{resp.status_code}] {name}")
        if resp.status_code != 200:
            print(f"ERROR: {resp.text}")
            sys.exit(1)

    print("ALL API ENDPOINTS RETURNED HTTP 200 OK!")

if __name__ == "__main__":
    main()
