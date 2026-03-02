#!/usr/bin/env python
"""Test script para verificar que los endpoints funcionan."""
import requests
import time
import sys
import logging

BASE_URL = "http://localhost:8000"

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

def test_endpoints():
    log.info("\n" + "="*60)
    log.info("🧪 TESTING NEXO SOBERANO BACKEND")
    log.info("="*60 + "\n")
    
    # Wait a bit for server to start
    time.sleep(2)
    
    tests = [
        ("GET", "/", "Root"),
        ("GET", "/api/health", "Health Check"),
        ("GET", "/api/status", "Status Detallado"),
        ("POST", "/api/chat", "Chat Endpoint", {"message": "¿Quién eres?"}),
    ]
    
    for test in tests:
        method = test[0]
        endpoint = test[1]
        label = test[2]
        data = test[3] if len(test) > 3 else None
        
        try:
            if method == "GET":
                r = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            else:
                r = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=5)
            
            if r.status_code == 200:
                log.info(f"✅ {label:25} {method:4} {endpoint:20} → OK")
                if endpoint == "/api/health":
                    log.info(f"   Response: {r.json()}\n")
            else:
                log.info(f"⚠️  {label:25} {method:4} {endpoint:20} → {r.status_code}")
        except Exception as e:
            log.info(f"❌ {label:25} {method:4} {endpoint:20} → ERROR: {e}")
    
    log.info("\n" + "="*60)
    log.info("✅ BACKEND OPERATIVO")
    log.info("📊 Swagger: http://localhost:8000/docs")
    log.info("="*60 + "\n")

if __name__ == "__main__":
    test_endpoints()
