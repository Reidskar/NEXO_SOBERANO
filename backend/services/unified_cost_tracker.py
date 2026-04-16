"""
Sistema unificado de tracking de costos operacionales - NEXO SOBERANO
Registra y calcula costos reales de todos los servicios:
- APIs de IA (Gemini, Claude, OpenAI, Grok)
- Servicios externos (Google Drive, Microsoft, X/Twitter, Discord)
"""

import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend import config

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════
# TABLAS DE PRICING (USD por millón de tokens/llamadas)
# ════════════════════════════════════════════════════════════════════

PRICING_AI_PROVIDERS = {
    # Google Gemini (Free tier hasta 900K tokens/día)
    "gemini-2.5-flash-lite": {"input": 0.0, "output": 0.0, "free_tier_daily": 900_000},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30, "free_tier_daily": 1_500_000},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.0, "free_tier_daily": 0},
    "gemini-2.5-pro": {"input": 2.50, "output": 10.0, "free_tier_daily": 0},
    "gemini-embedding": {"input": 0.00125, "output": 0.0, "free_tier_daily": 0},
    
    # Anthropic Claude
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0, "free_tier_daily": 0},
    "claude-3-opus": {"input": 15.0, "output": 75.0, "free_tier_daily": 0},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0, "free_tier_daily": 0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0, "free_tier_daily": 0},
    
    # OpenAI
    "gpt-4.1-mini": {"input": 0.15, "output": 0.60, "free_tier_daily": 0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0, "free_tier_daily": 0},
    "gpt-4o": {"input": 2.50, "output": 10.0, "free_tier_daily": 0},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "free_tier_daily": 0},
    
    # xAI Grok (Beta pricing estimado)
    "grok-beta": {"input": 2.0, "output": 6.0, "free_tier_daily": 0},
    "grok-2": {"input": 2.0, "output": 6.0, "free_tier_daily": 0},

    # Ollama local (costo $0 — se registran tokens para métricas)
    "gemma4": {"input": 0.0, "output": 0.0, "free_tier_daily": 0},
    "gemma4:latest": {"input": 0.0, "output": 0.0, "free_tier_daily": 0},
    "gemma3:27b": {"input": 0.0, "output": 0.0, "free_tier_daily": 0},
    "gemma3:12b": {"input": 0.0, "output": 0.0, "free_tier_daily": 0},
    "gemma3:4b": {"input": 0.0, "output": 0.0, "free_tier_daily": 0},
    "gemma3:1b": {"input": 0.0, "output": 0.0, "free_tier_daily": 0},
    "qwen2.5-coder:7b": {"input": 0.0, "output": 0.0, "free_tier_daily": 0},
    "qwen3.5:latest": {"input": 0.0, "output": 0.0, "free_tier_daily": 0},
    "gemma2:9b": {"input": 0.0, "output": 0.0, "free_tier_daily": 0},
}

# Costos estimados de servicios externos (por operación o mensual)
PRICING_EXTERNAL_SERVICES = {
    "google_drive_api": {
        "cost_type": "quota",  # Gratis hasta cierto límite
        "free_daily_queries": 1_000_000,
        "cost_per_million_after": 0.0,  # Gratis en tier usuario normal
    },
    "microsoft_graph": {
        "cost_type": "quota",
        "free_daily_queries": 100_000,
        "cost_per_million_after": 0.0,  # Incluido en Microsoft 365
    },
    "x_twitter_api": {
        "cost_type": "monthly_subscription",
        "free_tier": False,
        "basic_monthly_usd": 100.0,  # API v2 Basic
        "monthly_tweet_limit": 10_000,
    },
    "discord_webhook": {
        "cost_type": "free",
        "monthly_cost": 0.0,
    },
    "obs_websocket": {
        "cost_type": "free",
        "monthly_cost": 0.0,  # Software local
    },
}


class UnifiedCostTracker:
    """
    Sistema unificado de tracking de costos operacionales.
    
    Tablas SQL:
    - costos_ia: registro de llamadas a IA (fecha, provider, modelo, tokens_in, tokens_out, costo_usd)
    - costos_servicios: registro de uso de servicios externos (fecha, servicio, operaciones, costo_estimado_usd)
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DB_PATH
        self._ensure_tables()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Retorna conexión a SQLite"""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_tables(self):
        """Crea tablas de costos si no existen"""
        conn = self._get_conn()
        
        # Tabla de costos de IA
        conn.execute("""
            CREATE TABLE IF NOT EXISTS costos_ia (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha           TEXT NOT NULL,
                provider        TEXT NOT NULL,
                modelo          TEXT NOT NULL,
                tokens_in       INTEGER NOT NULL,
                tokens_out      INTEGER NOT NULL,
                costo_usd       REAL NOT NULL,
                operacion       TEXT,
                metadata        TEXT
            )
        """)
        
        # Tabla de costos de servicios externos
        conn.execute("""
            CREATE TABLE IF NOT EXISTS costos_servicios (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha           TEXT NOT NULL,
                servicio        TEXT NOT NULL,
                operaciones     INTEGER NOT NULL,
                costo_estimado  REAL NOT NULL,
                tipo_operacion  TEXT,
                metadata        TEXT
            )
        """)
        
        # Índices para queries rápidas
        conn.execute("CREATE INDEX IF NOT EXISTS idx_costos_ia_fecha ON costos_ia(fecha)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_costos_ia_provider ON costos_ia(provider)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_costos_servicios_fecha ON costos_servicios(fecha)")
        
        conn.commit()
        conn.close()
    
    # ════════════════════════════════════════════════════════════════
    # REGISTRO DE COSTOS IA
    # ════════════════════════════════════════════════════════════════
    
    def track_ai_call(
        self,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        operacion: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Registra una llamada a API de IA y calcula su costo.
        
        Args:
            provider: "gemini", "anthropic", "openai", "grok"
            model: nombre del modelo (e.g., "gemini-1.5-flash")
            tokens_in: tokens de entrada
            tokens_out: tokens de salida
            operacion: descripción (e.g., "rag_consulta", "clasificacion")
            metadata: dict opcional con info adicional
        """
        try:
            # Calcular costo
            costo_usd = self._calculate_ai_cost(model, tokens_in, tokens_out)
            
            # Registrar en DB
            conn = self._get_conn()
            conn.execute(
                """
                INSERT INTO costos_ia 
                (fecha, provider, modelo, tokens_in, tokens_out, costo_usd, operacion, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    provider,
                    model,
                    tokens_in,
                    tokens_out,
                    costo_usd,
                    operacion,
                    str(metadata) if metadata else ""
                )
            )
            conn.commit()
            conn.close()
            
            logger.debug(
                f"Cost tracked: {provider}/{model} | "
                f"{tokens_in}→{tokens_out} tokens | "
                f"${costo_usd:.6f} | {operacion}"
            )
            
        except Exception as e:
            logger.error(f"Error tracking AI cost: {e}")
    
    def _calculate_ai_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        """Calcula costo en USD de una llamada a IA"""
        pricing = PRICING_AI_PROVIDERS.get(model)
        
        if not pricing:
            logger.warning(f"Pricing no encontrado para modelo: {model}")
            return 0.0
        
        # Costo por millón de tokens
        cost_in = (tokens_in / 1_000_000) * pricing["input"]
        cost_out = (tokens_out / 1_000_000) * pricing["output"]
        
        return cost_in + cost_out
    
    # ════════════════════════════════════════════════════════════════
    # REGISTRO DE SERVICIOS EXTERNOS
    # ════════════════════════════════════════════════════════════════
    
    def track_service_call(
        self,
        servicio: str,
        operaciones: int = 1,
        tipo_operacion: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Registra uso de servicio externo.
        
        Args:
            servicio: "google_drive_api", "microsoft_graph", "x_twitter_api", etc.
            operaciones: número de operaciones/llamadas
            tipo_operacion: "query", "upload", "download", etc.
            metadata: info adicional
        """
        try:
            # Estimar costo
            costo_estimado = self._estimate_service_cost(servicio, operaciones)
            
            conn = self._get_conn()
            conn.execute(
                """
                INSERT INTO costos_servicios
                (fecha, servicio, operaciones, costo_estimado, tipo_operacion, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    servicio,
                    operaciones,
                    costo_estimado,
                    tipo_operacion,
                    str(metadata) if metadata else ""
                )
            )
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error tracking service cost: {e}")
    
    def _estimate_service_cost(self, servicio: str, operaciones: int) -> float:
        """Estima costo de servicio externo"""
        pricing = PRICING_EXTERNAL_SERVICES.get(servicio)
        
        if not pricing:
            return 0.0
        
        cost_type = pricing.get("cost_type")
        
        if cost_type == "free":
            return 0.0
        elif cost_type == "quota":
            # Servicios con quota gratis generalmente no cobran extra
            return 0.0
        elif cost_type == "monthly_subscription":
            # Prorrateamos costo mensual por día
            monthly = pricing.get("basic_monthly_usd", 0.0)
            return monthly / 30.0  # Costo diario estimado
        
        return 0.0
    
    # ════════════════════════════════════════════════════════════════
    # REPORTES Y ANÁLISIS
    # ════════════════════════════════════════════════════════════════
    
    def get_cost_report(self, period: str = "today") -> Dict[str, Any]:
        """
        Genera reporte completo de costos.
        
        Args:
            period: "today", "week", "month", "all"
        
        Returns:
            {
                "period": "today",
                "date_range": {"start": "...", "end": "..."},
                "ai_providers": {
                    "gemini": {"calls": X, "tokens": Y, "cost_usd": Z},
                    "anthropic": {...},
                    ...
                },
                "external_services": {
                    "google_drive_api": {"calls": X, "cost_usd": Y},
                    ...
                },
                "total_cost_usd": XXX,
                "breakdown_by_operation": [...],
                "warnings": [...]
            }
        """
        date_range = self._get_date_range(period)
        
        # Costos de IA por provider
        ai_costs = self._get_ai_costs_by_provider(date_range)
        
        # Costos de servicios externos
        service_costs = self._get_service_costs(date_range)
        
        # Total
        total_ai = sum(p["cost_usd"] for p in ai_costs.values())
        total_services = sum(s["cost_usd"] for s in service_costs.values())
        total = total_ai + total_services
        
        # Warnings
        warnings = self._generate_warnings(ai_costs, service_costs, period)
        
        # Breakdown por operación
        operations_breakdown = self._get_operations_breakdown(date_range)
        
        return {
            "period": period,
            "date_range": date_range,
            "ai_providers": ai_costs,
            "external_services": service_costs,
            "total_cost_usd": round(total, 4),
            "total_ai_cost_usd": round(total_ai, 4),
            "total_services_cost_usd": round(total_services, 4),
            "breakdown_by_operation": operations_breakdown,
            "warnings": warnings,
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_date_range(self, period: str) -> Dict[str, str]:
        """Calcula rango de fechas según período"""
        now = datetime.now()
        
        if period == "today":
            start = date.today().isoformat()
            end = now.isoformat()
        elif period == "week":
            start = (now - timedelta(days=7)).date().isoformat()
            end = now.isoformat()
        elif period == "month":
            start = (now - timedelta(days=30)).date().isoformat()
            end = now.isoformat()
        else:  # all
            start = "2000-01-01"
            end = now.isoformat()
        
        return {"start": start, "end": end}
    
    def _get_ai_costs_by_provider(self, date_range: Dict[str, str]) -> Dict[str, Any]:
        """Obtiene costos de IA agrupados por provider"""
        conn = self._get_conn()
        
        rows = conn.execute(
            """
            SELECT 
                provider,
                COUNT(*) as calls,
                SUM(tokens_in) as total_tokens_in,
                SUM(tokens_out) as total_tokens_out,
                SUM(costo_usd) as total_cost
            FROM costos_ia
            WHERE fecha >= ? AND fecha <= ?
            GROUP BY provider
            """,
            (date_range["start"], date_range["end"])
        ).fetchall()
        
        conn.close()
        
        result = {}
        for row in rows:
            provider = row["provider"]
            result[provider] = {
                "calls": row["calls"],
                "tokens_in": row["total_tokens_in"],
                "tokens_out": row["total_tokens_out"],
                "total_tokens": row["total_tokens_in"] + row["total_tokens_out"],
                "cost_usd": round(row["total_cost"], 4)
            }
        
        return result
    
    def _get_service_costs(self, date_range: Dict[str, str]) -> Dict[str, Any]:
        """Obtiene costos de servicios externos"""
        conn = self._get_conn()
        
        rows = conn.execute(
            """
            SELECT 
                servicio,
                SUM(operaciones) as total_ops,
                SUM(costo_estimado) as total_cost
            FROM costos_servicios
            WHERE fecha >= ? AND fecha <= ?
            GROUP BY servicio
            """,
            (date_range["start"], date_range["end"])
        ).fetchall()
        
        conn.close()
        
        result = {}
        for row in rows:
            servicio = row["servicio"]
            result[servicio] = {
                "operations": row["total_ops"],
                "cost_usd": round(row["total_cost"], 4)
            }
        
        return result
    
    def _get_operations_breakdown(self, date_range: Dict[str, str]) -> List[Dict[str, Any]]:
        """Breakdown de costos por tipo de operación"""
        conn = self._get_conn()
        
        rows = conn.execute(
            """
            SELECT 
                operacion,
                provider,
                COUNT(*) as count,
                SUM(costo_usd) as cost
            FROM costos_ia
            WHERE fecha >= ? AND fecha <= ? AND operacion != ''
            GROUP BY operacion, provider
            ORDER BY cost DESC
            LIMIT 10
            """,
            (date_range["start"], date_range["end"])
        ).fetchall()
        
        conn.close()
        
        return [
            {
                "operation": row["operacion"],
                "provider": row["provider"],
                "count": row["count"],
                "cost_usd": round(row["cost"], 4)
            }
            for row in rows
        ]
    
    def _generate_warnings(
        self,
        ai_costs: Dict[str, Any],
        service_costs: Dict[str, Any],
        period: str
    ) -> List[str]:
        """Genera advertencias sobre costos anormales"""
        warnings = []
        
        # Warning si se está usando modelos caros
        gemini_cost = ai_costs.get("gemini", {}).get("cost_usd", 0)
        if gemini_cost > 1.0 and period == "today":
            warnings.append(
                f"⚠️ Gemini cost today: ${gemini_cost:.2f}. "
                "Consider using gemini-2.5-flash-lite (free tier) instead of Pro models."
            )
        
        # Warning si Anthropic/OpenAI está costando mucho
        anthropic_cost = ai_costs.get("anthropic", {}).get("cost_usd", 0)
        if anthropic_cost > 5.0 and period == "today":
            warnings.append(
                f"🚨 Anthropic Claude cost today: ${anthropic_cost:.2f}. "
                "High usage detected. Consider switching to cheaper models."
            )
        
        openai_cost = ai_costs.get("openai", {}).get("cost_usd", 0)
        if openai_cost > 5.0 and period == "today":
            warnings.append(
                f"🚨 OpenAI cost today: ${openai_cost:.2f}. "
                "High usage detected."
            )
        
        # Warning de free tier excedido
        gemini_tokens = ai_costs.get("gemini", {}).get("total_tokens", 0)
        if gemini_tokens > 900_000 and period == "today":
            warnings.append(
                f"⚠️ Gemini free tier exceeded: {gemini_tokens:,} tokens today. "
                "Additional calls may incur charges."
            )
        
        return warnings
    
    def get_daily_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """Resumen diario de costos de los últimos N días"""
        conn = self._get_conn()
        
        rows = conn.execute(
            """
            SELECT 
                DATE(fecha) as day,
                SUM(costo_usd) as daily_cost
            FROM costos_ia
            WHERE fecha >= date('now', '-' || ? || ' days')
            GROUP BY DATE(fecha)
            ORDER BY day DESC
            """,
            (days,)
        ).fetchall()
        
        conn.close()
        
        return [
            {
                "date": row["day"],
                "cost_usd": round(row["daily_cost"], 4)
            }
            for row in rows
        ]
    
    def get_budget_status(self) -> Dict[str, Any]:
        """Estado actual del presupuesto diario (Gemini free tier principalmente)"""
        conn = self._get_conn()
        
        # Tokens Gemini hoy
        today = date.today().isoformat()
        row = conn.execute(
            """
            SELECT 
                COALESCE(SUM(tokens_in + tokens_out), 0) as gemini_tokens_today
            FROM costos_ia
            WHERE fecha LIKE ? || '%' AND provider = 'gemini'
            """,
            (today,)
        ).fetchone()
        
        conn.close()
        
        gemini_tokens = row["gemini_tokens_today"] if row else 0
        free_tier_limit = 900_000
        
        return {
            "gemini_tokens_today": gemini_tokens,
            "gemini_free_tier_limit": free_tier_limit,
            "gemini_remaining": max(0, free_tier_limit - gemini_tokens),
            "gemini_usage_percent": round((gemini_tokens / free_tier_limit) * 100, 1),
            "can_operate": gemini_tokens < free_tier_limit,
            "date": today
        }


# ════════════════════════════════════════════════════════════════
# INSTANCIA GLOBAL
# ════════════════════════════════════════════════════════════════

_tracker: Optional[UnifiedCostTracker] = None

def get_cost_tracker() -> UnifiedCostTracker:
    """Obtiene tracker global de costos"""
    global _tracker
    if _tracker is None:
        _tracker = UnifiedCostTracker()
    return _tracker
