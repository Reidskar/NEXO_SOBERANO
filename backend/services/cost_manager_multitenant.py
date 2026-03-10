"""
backend/services/cost_manager_multitenant.py
============================================
CostManager rediseñado para:
  1. Multi-tenant: presupuesto separado por empresa
  2. Caché semántico: si dos preguntas similares ya fueron respondidas,
     reutiliza la respuesta SIN llamar a la API (ahorro real)
  3. Modelo waterfall: primero modelos baratos, luego caros solo si es necesario
  4. Embedding local: sentence-transformers corre en CPU, costo = $0
"""

import hashlib
import json
import os
from datetime import date, datetime
from typing import Optional
import redis
import psycopg2
from psycopg2.extras import RealDictCursor

# ── Configuración ──────────────────────────────────────────────
REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://nexo:password@localhost:5432/nexo_soberano")

# ── Límites por plan ───────────────────────────────────────────
PLAN_LIMITS = {
    "starter":    50_000,   # ~$0.05/día en Gemini Flash
    "pro":       200_000,   # ~$0.20/día
    "enterprise": 900_000,  # ~$0.90/día
}

# ── Costo aproximado por 1k tokens (USD) ──────────────────────
# Usamos esto solo para reportes, no para enforcement
TOKEN_COSTS_PER_1K = {
    "gemini-1.5-flash":     0.000075,   # MÁS BARATO — usar primero
    "gemini-1.5-pro":       0.00125,
    "gpt-4o-mini":          0.000150,
    "gpt-4o":               0.005,
    "gpt-4":                0.01,       # MÁS CARO — usar solo si necesario
    "grok-beta":            0.005,
    "local-embedding":      0.0,        # sentence-transformers = gratis
}

# TTL del caché semántico (segundos)
SEMANTIC_CACHE_TTL = 3600 * 4  # 4 horas


class CostManagerMultiTenant:
    """
    Gestiona costos por tenant con caché semántico agresivo.
    """

    def __init__(self, tenant_slug: str):
        self.tenant_slug = tenant_slug
        self.schema = f"tenant_{tenant_slug.replace('-', '_')}"
        self._redis = redis.from_url(REDIS_URL, decode_responses=True)
        self._embedding_model = None  # Lazy load

    def _pg(self):
        """Conexión PostgreSQL (crear nueva por llamada para thread-safety)."""
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

    def _get_plan_limit(self) -> int:
        """Obtiene el límite diario del plan del tenant."""
        cache_key = f"nexo:plan:{self.tenant_slug}"
        cached = self._redis.get(cache_key)
        if cached:
            return int(cached)

        try:
            with self._pg() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT plan, max_tokens_dia FROM tenants WHERE slug = %s",
                        (self.tenant_slug,)
                    )
                    row = cur.fetchone()
                    if row:
                        limit = row["max_tokens_dia"] or PLAN_LIMITS.get(row["plan"], 50_000)
                        self._redis.setex(cache_key, 3600, str(limit))
                        return limit
        except Exception:
            pass
        return PLAN_LIMITS["starter"]

    # ── PRESUPUESTO ────────────────────────────────────────────

    def tokens_hoy(self) -> int:
        """Tokens usados hoy por este tenant (con caché Redis 30s)."""
        cache_key = f"nexo:tokens_hoy:{self.tenant_slug}:{date.today().isoformat()}"
        cached = self._redis.get(cache_key)
        if cached:
            return int(cached)

        try:
            with self._pg() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT COALESCE(SUM(tokens_in + tokens_out), 0) as total "
                        f"FROM {self.schema}.api_costs WHERE fecha = CURRENT_DATE"
                    )
                    total = cur.fetchone()["total"]
                    self._redis.setex(cache_key, 30, str(total))
                    return int(total)
        except Exception:
            return 0

    def puede_operar(self, tokens_estimados: int = 1000) -> bool:
        """¿Puede este tenant hacer otra consulta?"""
        return (self.tokens_hoy() + tokens_estimados) < self._get_plan_limit()

    def estado(self) -> dict:
        """Estado completo del presupuesto del tenant."""
        hoy = self.tokens_hoy()
        limite = self._get_plan_limit()
        return {
            "tenant": self.tenant_slug,
            "tokens_hoy": hoy,
            "limite_diario": limite,
            "disponibles": max(0, limite - hoy),
            "porcentaje_usado": round((hoy / limite) * 100, 1) if limite > 0 else 0,
            "puede_operar": hoy < limite,
            "fecha": date.today().isoformat(),
        }

    def registrar(self, model: str, tokens_in: int, tokens_out: int,
                   operation: str, user_id: Optional[str] = None):
        """Registra un uso de API en la DB y invalida caché."""
        try:
            with self._pg() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        INSERT INTO {self.schema}.api_costs
                        (user_id, model, tokens_in, tokens_out, operation)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, model, tokens_in, tokens_out, operation))
                conn.commit()

            # Invalidar caché para que el próximo puede_operar() sea fresco
            cache_key = f"nexo:tokens_hoy:{self.tenant_slug}:{date.today().isoformat()}"
            self._redis.delete(cache_key)

        except Exception as e:
            print(f"⚠️  Error registrando costo: {e}")

    # ── CACHÉ SEMÁNTICO ────────────────────────────────────────
    # La idea: si la misma pregunta (o muy similar) ya fue respondida,
    # devolver la respuesta cacheada sin tocar la API.
    # Ahorro estimado: 40-60% de tokens en uso real.

    def _get_embedding_model(self):
        """Carga el modelo de embedding local (solo una vez)."""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            except ImportError:
                pass
        return self._embedding_model

    def _query_fingerprint(self, query: str) -> str:
        """Hash MD5 de la query normalizada (caché exacto)."""
        normalized = query.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get_cached_response(self, query: str) -> Optional[dict]:
        """
        Busca respuesta cacheada para esta query.
        Primero caché exacto (hash), luego semántico si está disponible.
        """
        # 1. Caché exacto (más rápido, < 1ms)
        exact_key = f"nexo:cache:exact:{self.tenant_slug}:{self._query_fingerprint(query)}"
        cached = self._redis.get(exact_key)
        if cached:
            data = json.loads(cached)
            data["_cache_hit"] = "exact"
            return data

        # 2. Caché semántico (más flexible, usa embeddings locales)
        model = self._get_embedding_model()
        if model is None:
            return None

        try:
            import numpy as np
            query_vec = model.encode(query).tolist()
            query_vec_key = f"nexo:cache:semantic:{self.tenant_slug}"

            # Buscar en Redis los vectores recientes de este tenant
            # (guardamos los últimos 100 embeddings)
            members = self._redis.lrange(f"{query_vec_key}:keys", 0, 99)

            best_score = 0.0
            best_key = None

            for member_key in members:
                stored = self._redis.get(f"{query_vec_key}:{member_key}")
                if not stored:
                    continue
                stored_data = json.loads(stored)
                stored_vec = stored_data.get("embedding", [])
                if not stored_vec:
                    continue

                # Similitud coseno
                a = np.array(query_vec)
                b = np.array(stored_vec)
                score = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))

                if score > best_score:
                    best_score = score
                    best_key = member_key

            # Umbral: 0.92 = muy similar (no 0.65 como el RAG normal)
            # Para caché queremos alta precisión, no recall
            if best_score >= 0.92 and best_key:
                stored_data = json.loads(self._redis.get(f"{query_vec_key}:{best_key}"))
                result = stored_data.get("response", {})
                result["_cache_hit"] = f"semantic:{best_score:.3f}"
                return result

        except Exception:
            pass

        return None

    def set_cached_response(self, query: str, response: dict):
        """Guarda respuesta en caché exacto y semántico."""
        # Caché exacto
        exact_key = f"nexo:cache:exact:{self.tenant_slug}:{self._query_fingerprint(query)}"
        self._redis.setex(exact_key, SEMANTIC_CACHE_TTL, json.dumps(response))

        # Caché semántico con embedding
        model = self._get_embedding_model()
        if model is None:
            return

        try:
            query_vec = model.encode(query).tolist()
            member_key = self._query_fingerprint(query)
            vec_key = f"nexo:cache:semantic:{self.tenant_slug}:{member_key}"

            self._redis.setex(vec_key, SEMANTIC_CACHE_TTL, json.dumps({
                "embedding": query_vec,
                "response": response,
                "query": query[:200],
                "cached_at": datetime.now().isoformat(),
            }))

            # Mantener lista de keys para búsqueda semántica
            list_key = f"nexo:cache:semantic:{self.tenant_slug}:keys"
            self._redis.lpush(list_key, member_key)
            self._redis.ltrim(list_key, 0, 99)   # Máximo 100 entradas
            self._redis.expire(list_key, SEMANTIC_CACHE_TTL)

        except Exception as e:
            pass  # El caché semántico es opcional, no bloquear

    # ── SELECTOR DE MODELO ÓPTIMO ──────────────────────────────

    @staticmethod
    def modelo_optimo(tipo_operacion: str) -> str:
        """
        Devuelve el modelo más barato que puede manejar la operación.

        Estrategia waterfall de costo:
        - Embeddings → local (gratis)
        - Preguntas simples / RAG → gemini-1.5-flash (más barato)
        - Razonamiento complejo → gemini-1.5-pro
        - Validación X/Twitter → grok-beta (solo para esto)
        - GPT-4 → NUNCA de forma automática (solo si usuario lo pide explícitamente)
        """
        mapa = {
            "embedding":          "local-embedding",
            "rag_consulta":       "gemini-1.5-flash",
            "chat_simple":        "gemini-1.5-flash",
            "chat_complejo":      "gemini-1.5-pro",
            "analisis":           "gemini-1.5-pro",
            "resumen":            "gemini-1.5-flash",
            "clasificacion":      "gemini-1.5-flash",
            "twitter_validation": "grok-beta",
            "email_digest":       "gemini-1.5-flash",
        }
        return mapa.get(tipo_operacion, "gemini-1.5-flash")  # Default al más barato

    def costo_estimado_usd(self, tokens: int, model: str) -> float:
        """Estima costo en USD para N tokens del modelo dado."""
        rate = TOKEN_COSTS_PER_1K.get(model, 0.001)
        return (tokens / 1000) * rate

    def reporte_costos_7dias(self) -> dict:
        """Historial de costos por día y modelo (últimos 7 días)."""
        try:
            with self._pg() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        SELECT
                            fecha,
                            model,
                            SUM(tokens_in + tokens_out) as tokens_total,
                            COUNT(*) as llamadas
                        FROM {self.schema}.api_costs
                        WHERE fecha >= CURRENT_DATE - INTERVAL '7 days'
                        GROUP BY fecha, model
                        ORDER BY fecha DESC, tokens_total DESC
                    """)
                    rows = cur.fetchall()
                    return {"datos": [dict(r) for r in rows]}
        except Exception as e:
            return {"error": str(e)}
