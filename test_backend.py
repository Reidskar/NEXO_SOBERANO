#!/usr/bin/env python
"""
NEXO SOBERANO - Test Suite Integral
Verifica: imports, Docker, embeddings, endpoints API, RAG service
Uso: .venv/Scripts/python.exe test_backend.py
"""
import sys
import os
import time
import json
import logging
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
log = logging.getLogger(__name__)

BASE_URL = os.getenv("NEXO_TEST_URL", "http://localhost:8080")

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = {"pass": 0, "fail": 0, "warn": 0}


def ok(msg):
    log.info(f"  {PASS} {msg}")
    results["pass"] += 1


def fail(msg):
    log.info(f"  {FAIL} {msg}")
    results["fail"] += 1


def warn(msg):
    log.info(f"  {WARN} {msg}")
    results["warn"] += 1


def section(title):
    log.info(f"\n{'─'*60}")
    log.info(f"  {title}")
    log.info(f"{'─'*60}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. IMPORTS CRÍTICOS
# ══════════════════════════════════════════════════════════════════════════════
section("1 · IMPORTS CRÍTICOS")

try:
    import requests
    ok("requests disponible")
except ImportError:
    fail("requests no instalado")

try:
    from dotenv import load_dotenv
    ok("python-dotenv disponible")
except ImportError:
    fail("python-dotenv no instalado")

try:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import google.generativeai as _genai_legacy
    ok("google-generativeai (legacy) disponible")
except ImportError:
    warn("google-generativeai no instalado (reemplazado por google-genai)")

try:
    from google import genai as new_genai
    ok(f"google-genai (nueva SDK) disponible — v{new_genai.__version__}")
except ImportError:
    fail("google-genai no instalado")

try:
    import anthropic
    ok("anthropic SDK disponible")
except ImportError:
    warn("anthropic no instalado (opcional, fallback a Gemini)")

try:
    import chromadb
    ok(f"chromadb disponible — v{chromadb.__version__}")
except ImportError:
    warn("chromadb no instalado (RAG local degradado)")

try:
    import qdrant_client
    try:
        _qv = qdrant_client.version.VERSION
    except Exception:
        _qv = "instalado"
    ok(f"qdrant-client disponible — v{_qv}")
except ImportError:
    fail("qdrant-client no instalado")

try:
    import fastapi
    ok(f"fastapi disponible — v{fastapi.__version__}")
except ImportError:
    fail("fastapi no instalado")

try:
    import uvicorn
    ok("uvicorn disponible")
except ImportError:
    fail("uvicorn no instalado")

# ══════════════════════════════════════════════════════════════════════════════
# 2. CONFIGURACIÓN Y VARIABLES DE ENTORNO
# ══════════════════════════════════════════════════════════════════════════════
section("2 · CONFIGURACIÓN")

try:
    from backend import config
    ok("backend.config importado")

    checks = [
        ("GEMINI_API_KEY",    config.GEMINI_API_KEY),
        ("DATABASE_URL",      config.DATABASE_URL),
        ("MODELO_FLASH",      config.MODELO_FLASH),
        ("LLM_PROVIDER",      config.LLM_PROVIDER),
        ("NEXO_MODE",         config.NEXO_MODE),
    ]
    for name, val in checks:
        if val:
            ok(f"{name} = {val[:30]}..." if len(str(val)) > 30 else f"{name} = {val}")
        else:
            warn(f"{name} vacío o no configurado")

    # Opcionales
    for name, val in [
        ("ANTHROPIC_API_KEY", config.ANTHROPIC_API_KEY),
        ("SUPABASE_URL",      config.SUPABASE_URL),
        ("UPSTASH_REDIS_URL", config.UPSTASH_REDIS_URL),
        ("XAI_API_KEY",       config.XAI_API_KEY),
    ]:
        if val:
            ok(f"{name} configurado")
        else:
            warn(f"{name} no configurado (opcional)")
except Exception as e:
    fail(f"backend.config — ERROR: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 3. DOCKER — CONECTIVIDAD DE SERVICIOS
# ══════════════════════════════════════════════════════════════════════════════
section("3 · DOCKER — CONECTIVIDAD")

# PostgreSQL
try:
    import psycopg2
    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        conn = psycopg2.connect(db_url, connect_timeout=3)
        conn.close()
        ok("PostgreSQL (nexo_db) — conectado")
    else:
        try:
            conn = psycopg2.connect(
                host="localhost", port=5432,
                dbname="nexo", user="nexo",
                password=os.getenv("POSTGRES_PASSWORD", ""),
                connect_timeout=3
            )
            conn.close()
            ok("PostgreSQL (nexo_db) — conectado vía localhost")
        except Exception as e:
            warn(f"PostgreSQL no accesible: {e}")
except ImportError:
    warn("psycopg2 no instalado — skip test PostgreSQL")
except Exception as e:
    fail(f"PostgreSQL — ERROR: {e}")

# Redis
try:
    import redis as redis_lib
    r = redis_lib.Redis(host="localhost", port=6379, socket_connect_timeout=2)
    r.ping()
    ok("Redis (nexo_redis) — PONG")
except ImportError:
    warn("redis-py no instalado — skip test Redis")
except Exception as e:
    warn(f"Redis no accesible: {e}")

# Qdrant
try:
    from qdrant_client import QdrantClient
    qc = QdrantClient(host="localhost", port=6333, timeout=3)
    info = qc.get_collections()
    ok(f"Qdrant (nexo_qdrant) — conectado ({len(info.collections)} colecciones)")
except Exception as e:
    warn(f"Qdrant no accesible: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 4. GEMINI EMBEDDING 2
# ══════════════════════════════════════════════════════════════════════════════
section("4 · GEMINI EMBEDDING 2")

try:
    from utils.ai_core import embed_text_gemini2, embed_query_gemini2, GEMINI_EMBED_MODEL, GEMINI_EMBED_DIMS
    ok(f"utils.ai_core importado — modelo: {GEMINI_EMBED_MODEL} @ {GEMINI_EMBED_DIMS} dims")

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        warn("GEMINI_API_KEY no configurada — skip prueba real de embedding")
    else:
        t0 = time.time()
        vec = embed_text_gemini2("test de embedding nexo soberano", api_key=api_key)
        elapsed = int((time.time() - t0) * 1000)
        if vec and len(vec) == GEMINI_EMBED_DIMS:
            ok(f"embed_text_gemini2 → {len(vec)} dims en {elapsed}ms")
        elif vec:
            warn(f"embed_text_gemini2 → {len(vec)} dims (esperados {GEMINI_EMBED_DIMS})")
        else:
            fail("embed_text_gemini2 → None")

        t0 = time.time()
        vec_q = embed_query_gemini2("consulta de búsqueda", api_key=api_key)
        elapsed = int((time.time() - t0) * 1000)
        if vec_q and len(vec_q) == GEMINI_EMBED_DIMS:
            ok(f"embed_query_gemini2 → {len(vec_q)} dims en {elapsed}ms")
        else:
            fail(f"embed_query_gemini2 → falló")
except Exception as e:
    fail(f"Gemini Embedding 2 — ERROR: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 5. RAG SERVICE
# ══════════════════════════════════════════════════════════════════════════════
section("5 · RAG SERVICE")

try:
    from backend.services.rag_service import RAGService, generar_embedding, generar_embedding_query
    ok("rag_service importado")

    rag = RAGService()
    estado = rag.estado()
    ok(f"RAGService.estado() → status={estado.get('status')}, docs={estado.get('total_docs', '?')}")
except Exception as e:
    fail(f"RAGService — ERROR: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 6. ENDPOINTS HTTP (requiere backend corriendo)
# ══════════════════════════════════════════════════════════════════════════════
section(f"6 · ENDPOINTS HTTP ({BASE_URL})")

try:
    # Verificar que el backend esté vivo
    r = requests.get(f"{BASE_URL}/api/health", timeout=5)
    if r.status_code == 200:
        data = r.json()
        ok(f"GET /api/health → {data.get('version', 'ok')}")
    else:
        warn(f"GET /api/health → HTTP {r.status_code}")
except requests.exceptions.ConnectionError:
    warn(f"Backend no disponible en {BASE_URL} — skip tests HTTP")
    warn("Arranca con: .venv\\Scripts\\python.exe -m uvicorn backend.main:app --port 8000")
else:
    # (method, path, body, label, timeout_s)
    endpoints = [
        # Core — respuesta inmediata
        ("GET",  "/api/health",        None,                                           "Health",           5),
        ("GET",  "/api/status",        None,                                           "Status",           5),
        ("GET",  "/api/metrics",       None,                                           "Metrics",          5),
        ("GET",  "/docs",              None,                                           "Swagger UI",       5),
        # Auth
        ("POST", "/auth/login",        {"username":"admin","password":"nexo2026"},     "Auth login",       5),
        # AI — pueden tardar (llamadas a Gemini)
        ("POST", "/api/ai/ask",        {"question":"¿qué es NEXO Soberano?"},          "AI ask",          30),
        ("GET",  "/api/ai/status",     None,                                           "AI status",        5),
        ("POST", "/api/ai/consultar",  {"mensaje":"test"},                             "AI consultar",    30),
        # Knowledge
        ("GET",  "/api/knowledge/health", None,                                        "Knowledge health", 5),
        # Agente status (solo GET, no llama a AI)
        ("GET",  "/api/agente/status", None,                                           "Agente status",    5),
        # Agente consultar (llama a AI — timeout largo)
        ("POST", "/agente/consultar",  {"query":"¿cuál es tu función?"},               "Agente consultar",30),
    ]

    for method, path, body, label, tout in endpoints:
        try:
            if method == "GET":
                r = requests.get(f"{BASE_URL}{path}", timeout=tout)
            else:
                r = requests.post(f"{BASE_URL}{path}", json=body, timeout=tout)

            if r.status_code in (200, 201):
                ok(f"{method:4} {path:35} → {r.status_code} {label}")
            elif r.status_code in (401, 403):
                warn(f"{method:4} {path:35} → {r.status_code} {label} (auth requerida)")
            elif r.status_code == 404:
                warn(f"{method:4} {path:35} → 404 {label} (ruta no registrada)")
            elif r.status_code == 422:
                warn(f"{method:4} {path:35} → 422 {label} (validación — revisar body)")
            else:
                fail(f"{method:4} {path:35} → {r.status_code} {label}")
        except Exception as e:
            fail(f"{method:4} {path:35} → ERROR: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# RESUMEN
# ══════════════════════════════════════════════════════════════════════════════
total = results["pass"] + results["fail"] + results["warn"]
log.info(f"\n{'═'*60}")
log.info(f"  RESULTADO FINAL  |  {total} pruebas")
log.info(f"{'═'*60}")
log.info(f"  {PASS} PASS : {results['pass']}")
log.info(f"  {WARN}WARN : {results['warn']}")
log.info(f"  {FAIL} FAIL : {results['fail']}")
log.info(f"{'═'*60}")
log.info(f"  Swagger   → {BASE_URL}/docs")
log.info(f"  Redoc     → {BASE_URL}/redoc")
log.info(f"  Health    → {BASE_URL}/api/health")
log.info(f"{'═'*60}\n")

if results["fail"] > 0:
    sys.exit(1)
