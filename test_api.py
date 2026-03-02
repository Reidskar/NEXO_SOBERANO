#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Test 1: Health check
log.info("=" * 60)
log.info("TEST 1: Health Check")
log.info("=" * 60)
try:
    response = requests.get(f"{BASE_URL}/api/health")
    log.info(f"Status: {response.status_code}")
    log.info(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    log.info(f"Error: {e}")

# Test 2: Status endpoint
log.info("\n" + "=" * 60)
log.info("TEST 2: System Status")
log.info("=" * 60)
try:
    response = requests.get(f"{BASE_URL}/api/status")
    log.info(f"Status: {response.status_code}")
    log.info(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    log.info(f"Error: {e}")

# Test 3: Chat endpoint
log.info("\n" + "=" * 60)
log.info("TEST 3: Chat API")
log.info("=" * 60)
try:
    payload = {"message": "¿Qué es Nexo Soberano?"}
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    log.info(f"Status: {response.status_code}")
    log.info(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    log.info(f"Error: {e}")

# Test 4: Chat history endpoint
log.info("\n" + "=" * 60)
log.info("TEST 4: Chat History")
log.info("=" * 60)
try:
    response = requests.get(f"{BASE_URL}/api/chat/history")
    log.info(f"Status: {response.status_code}")
    log.info(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    log.info(f"Error: {e}")

log.info("\n" + "=" * 60)
log.info("API TESTS COMPLETE")
log.info("=" * 60)
