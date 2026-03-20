# ============================================================
# NEXO SOBERANO — Bridge: agente_postulaciones → Inter-Agent Bus
# © 2026 elanarcocapital.com
# ============================================================
from __future__ import annotations
import logging
import sys
from pathlib import Path

# Agregar raíz del repo al path para importar NEXO_CORE
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger("NEXO.postulaciones.bus_bridge")

try:
    from NEXO_CORE.tools.inter_agent_bus.service import InterAgentBus
    BUS_AVAILABLE = True
except ImportError:
    BUS_AVAILABLE = False
    logger.warning("Inter-Agent Bus no disponible — modo standalone")


def notificar_match_alto(
    job_title: str,
    company: str,
    match_score: float,
    job_url: str,
    salary_clp: int = 0
) -> bool:
    """
    Envía alerta al bus cuando se detecta oferta con
    match >= 85%. Notifica a nexo-sovereign y nexo-cfo.

    Args:
        job_title: Título del cargo
        company: Nombre de la empresa
        match_score: Porcentaje de match (0-100)
        job_url: URL de la oferta
        salary_clp: Salario en CLP si está disponible

    Returns:
        True si el mensaje fue enviado, False si bus no disponible
    """
    if not BUS_AVAILABLE:
        logger.info(f"[STANDALONE] Match {match_score}%: {job_title} en {company}")
        return False

    urgencia = "critical" if match_score >= 95 else "high"

    # Notificar a nexo-sovereign (alerta operacional)
    InterAgentBus.enviar(
        origen="agente_postulaciones",
        destino="nexo-sovereign",
        tipo="alerta",
        urgencia=urgencia,
        mensaje=f"Match {match_score:.0f}%: {job_title} en {company}",
        datos={
            "url": job_url,
            "score": match_score,
            "titulo": job_title,
            "empresa": company
        }
    )

    # Notificar a nexo-cfo solo si hay info de salario
    if salary_clp > 0:
        InterAgentBus.enviar(
            origen="agente_postulaciones",
            destino="nexo-cfo",
            tipo="info",
            urgencia="medium",
            mensaje=f"Oferta con banda salarial: {job_title} — ${salary_clp:,} CLP",
            datos={
                "url": job_url,
                "salary_clp": salary_clp,
                "empresa": company,
                "score": match_score
            }
        )

    logger.info(f"Bus notificado: {job_title} ({match_score:.0f}%) → {urgencia}")
    return True


def notificar_postulacion_enviada(
    job_title: str,
    company: str,
    job_url: str
) -> bool:
    """Notifica al bus cuando se envía una postulación."""
    if not BUS_AVAILABLE:
        return False

    InterAgentBus.enviar(
        origen="agente_postulaciones",
        destino="nexo-community",
        tipo="info",
        urgencia="low",
        mensaje=f"Postulación enviada: {job_title} en {company}",
        datos={"url": job_url, "empresa": company}
    )
    return True


if __name__ == "__main__":
    # Test rápido del bridge
    ok = notificar_match_alto(
        job_title="TEST Backend Developer",
        company="TEST Corp",
        match_score=92.5,
        job_url="https://example.com/test",
        salary_clp=2_500_000
    )
    print(f"[OK] Bridge test: mensaje enviado={ok}")
