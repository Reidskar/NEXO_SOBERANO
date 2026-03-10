import httpx
import os
import sys

# Configuración básica
BASE = "http://localhost:8000"
KEY = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")

tests = [
    ("GET", "/api/health", None, 200),
    ("GET", "/api/dashboard/health", None, 200),
    ("GET", "/api/dashboard/tenants", None, 200),
    ("GET", "/api/dashboard/stats?tenant_slug=demo", None, 200),
    ("GET", "/api/dashboard/token-history?tenant_slug=demo", None, 200),
    ("POST", "/api/webhooks/ingest", {"tenant_slug": "demo", "type": "test", "title": "smoke", "body": "test", "severity": 0.5}, 200),
]

def run_smoke_tests():
    print(f"[*] Iniciando Smoke Test en {BASE}...")
    headers = {"X-API-Key": KEY}
    
    passed = 0
    failed = 0
    
    for method, path, body, expected in tests:
        try:
            r = httpx.request(method, f"{BASE}{path}", json=body, headers=headers, timeout=30.0, follow_redirects=True)
            status = "[OK]" if r.status_code == expected else "[ERROR]"
            print(f"{status} {method} {path} -> Status: {r.status_code} (Esperado: {expected})")
            if r.status_code == expected:
                passed += 1
            else:
                print(f"       Detalle error: {r.text}")
                failed += 1
        except Exception as e:
            print(f"[FAIL] {method} {path} -> Error: {e}")
            failed += 1
            
    print("\n" + "="*40)
    print(f"RESULTADOS: {passed} Correctos, {failed} Fallidos")
    print("="*40)
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_smoke_tests()
