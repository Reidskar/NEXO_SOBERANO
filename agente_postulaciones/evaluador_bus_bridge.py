# ============================================================
# NEXO SOBERANO — Evaluador IA + Bus Bridge
# © 2026 elanarcocapital.com
# Conecta el scoring de postulaciones con el Inter-Agent Bus
# ============================================================
from __future__ import annotations
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger("NEXO.postulaciones.evaluador_bridge")

try:
    from NEXO_CORE.tools.inter_agent_bus.service import InterAgentBus
    BUS_AVAILABLE = True
except ImportError:
    BUS_AVAILABLE = False
    logger.warning("Bus no disponible — modo standalone")

try:
    from NEXO_CORE.services.ai_router import ai_router, AIRequest
    AI_ROUTER_AVAILABLE = True
except ImportError:
    AI_ROUTER_AVAILABLE = False
    logger.warning("AI Router no disponible — usando evaluador original")


async def evaluar_con_router(
    job_title: str,
    job_description: str,
    cv_profile: dict
) -> dict:
    """
    Evalúa una oferta laboral usando el AI Router soberano.
    Usa gemma2:9b local en vez de Gemini para el scoring.

    Args:
        job_title: Título del cargo
        job_description: Descripción de la oferta
        cv_profile: Perfil del candidato

    Returns:
        dict con score, justificacion, recomendacion
    """
    if not AI_ROUTER_AVAILABLE:
        return {"score": 0, "error": "AI Router no disponible"}

    skills = cv_profile.get("skills", [])
    roles  = cv_profile.get("roles_preferred", [])

    prompt = f"""Evalúa esta oferta laboral para el candidato.

OFERTA: {job_title}
DESCRIPCIÓN: {job_description[:500]}

PERFIL DEL CANDIDATO:
- Skills: {', '.join(skills[:10])}
- Roles buscados: {', '.join(roles[:5])}

Responde SOLO con un JSON con este formato exacto:
{{
  "score": <número del 0 al 100>,
  "justificacion": "<razón en máx 20 palabras>",
  "recomendacion": "<postular|evaluar|descartar>"
}}"""

    try:
        result = await ai_router.consultar(AIRequest(
            prompt=prompt,
            tipo="clasificacion",
            temperatura=0.05
        ))

        if result.success:
            import json, re
            text = result.texto
            match = re.search(r'\{.*?\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                score = float(data.get("score", 0))

                # Notificar al bus si score alto
                if score >= 80 and BUS_AVAILABLE:
                    InterAgentBus.enviar(
                        origen="agente_postulaciones",
                        destino="nexo-sovereign",
                        tipo="alerta",
                        urgencia="high" if score >= 90 else "medium",
                        mensaje=f"Score {score:.0f}%: {job_title}",
                        datos={
                            "score": score,
                            "titulo": job_title,
                            "recomendacion": data.get("recomendacion"),
                            "modelo_usado": result.modelo_usado,
                            "fuente": result.fuente
                        }
                    )
                    logger.info(
                        f"Bus notificado: {job_title} "
                        f"score={score} fuente={result.fuente}"
                    )

                return {
                    "score": score,
                    "justificacion": data.get("justificacion", ""),
                    "recomendacion": data.get("recomendacion", "evaluar"),
                    "modelo_usado": result.modelo_usado,
                    "fuente_ia": result.fuente
                }
    except Exception as e:
        logger.error(f"Error en evaluador_bus_bridge: {e}")

    return {"score": 0, "error": "No se pudo evaluar", "fuente_ia": "error"}


if __name__ == "__main__":
    import asyncio

    async def test():
        print("Test evaluador bridge...")
        result = await evaluar_con_router(
            job_title="Backend Developer Python",
            job_description="Buscamos desarrollador Python con FastAPI y Docker",
            cv_profile={
                "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
                "roles_preferred": ["backend developer", "python developer"]
            }
        )
        print(f"  Score:          {result.get('score')}")
        print(f"  Justificacion:  {result.get('justificacion')}")
        print(f"  Recomendacion:  {result.get('recomendacion')}")
        print(f"  Modelo usado:   {result.get('modelo_usado')}")
        print(f"  Fuente IA:      {result.get('fuente_ia')}")

    asyncio.run(test())
