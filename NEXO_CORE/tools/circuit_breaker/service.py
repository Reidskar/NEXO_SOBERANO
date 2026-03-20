# ============================================================
# NEXO SOBERANO — Circuit Breaker para Agentes
# © 2026 elanarcocapital.com
# Previene loops infinitos y gastos descontrolados de API
# ============================================================
from __future__ import annotations
import logging
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger("NEXO.circuit_breaker")

class CircuitState(BaseModel):
    agent_name: str
    state: str = "CLOSED"       # CLOSED=ok | OPEN=bloqueado | HALF_OPEN=probando
    failures: int = 0
    last_failure: Optional[str] = None
    opened_at: Optional[str] = None
    api_calls_today: int = 0
    api_cost_usd_today: float = 0.0

class CircuitBreaker:
    MAX_FAILURES = 3
    RESET_MINUTES = 30
    MAX_API_CALLS_PER_AGENT_PER_HOUR = 50
    MAX_COST_USD_PER_DAY = 2.00
    STATE_FILE = Path("logs/circuit_states.json")

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.state = self._load_state()

    def can_execute(self) -> tuple[bool, str]:
        if self.state.state == "OPEN":
            if self._should_attempt_reset():
                self.state.state = "HALF_OPEN"
                self._save_state()
                return True, "HALF_OPEN"
            return False, f"Circuit OPEN - demasiados fallos en {self.agent_name}"
        if self.state.api_cost_usd_today >= self.MAX_COST_USD_PER_DAY:
            return False, f"Límite de costo diario alcanzado: ${self.state.api_cost_usd_today}"
        if self.state.api_calls_today >= self.MAX_API_CALLS_PER_AGENT_PER_HOUR:
            return False, f"Límite de llamadas API alcanzado: {self.state.api_calls_today}"
        return True, "CLOSED"

    def record_success(self):
        self.state.failures = 0
        self.state.state = "CLOSED"
        self._save_state()
        logger.info(f"Circuit {self.agent_name}: éxito registrado")

    def record_failure(self, error: str):
        self.state.failures += 1
        self.state.last_failure = error
        if self.state.failures >= self.MAX_FAILURES:
            self.state.state = "OPEN"
            self.state.opened_at = datetime.now().isoformat()
            logger.error(f"Circuit {self.agent_name}: ABIERTO tras {self.state.failures} fallos")
        self._save_state()

    def record_api_call(self, cost_usd: float = 0.0):
        self.state.api_calls_today += 1
        self.state.api_cost_usd_today += cost_usd
        self._save_state()
        if self.state.api_cost_usd_today >= self.MAX_COST_USD_PER_DAY * 0.8:
            logger.warning(f"ALERTA CFO: {self.agent_name} en 80% del límite diario")

    def _should_attempt_reset(self) -> bool:
        if not self.state.opened_at:
            return False
        opened = datetime.fromisoformat(self.state.opened_at)
        return datetime.now() > opened + timedelta(minutes=self.RESET_MINUTES)

    def _load_state(self) -> CircuitState:
        self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(self.STATE_FILE.read_text())
            return CircuitState(**data.get(self.agent_name, {"agent_name": self.agent_name}))
        except:
            return CircuitState(agent_name=self.agent_name)

    def _save_state(self):
        try:
            existing = json.loads(self.STATE_FILE.read_text()) if self.STATE_FILE.exists() else {}
            existing[self.agent_name] = self.state.model_dump()
            self.STATE_FILE.write_text(json.dumps(existing, indent=2))
        except Exception as e:
            logger.error(f"Error guardando circuit state: {e}")

circuit_breakers = {
    agent: CircuitBreaker(agent)
    for agent in ["nexo-engineer","nexo-community","nexo-optimizer",
                  "nexo-cfo","nexo-sovereign","nexo-sentinel","nexo-forge"]
}
