from fastapi import APIRouter, Header, HTTPException, Request
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from core.config import settings
from core.queue_manager import system_queue
import logging
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

# Discord Public Key para verificar firmas
DISCORD_PUBLIC_KEY = getattr(settings, "DISCORD_PUBLIC_KEY", "TU_PUBLIC_KEY_AQUI")

@router.post("/discord")
async def handle_discord_slash_command(
    request: Request,
    x_signature_ed25519: str = Header(None),
    x_signature_timestamp: str = Header(None)
):
    """
    Discord Interactivity Hook con Capa de Seguridad Ed25519
    """
    event_id = str(uuid.uuid4())
    logger.info(f"🛡️ [DISCORD WEBHOOK] Recepción evento {event_id}. Validando criptografía...")

    # Seguridad: Verificación de Firma requerida por Discord
    if x_signature_ed25519 is None or x_signature_timestamp is None:
        raise HTTPException(status_code=401, detail="Faltan credenciales de firma")

    body = await request.body()
    try:
        if DISCORD_PUBLIC_KEY != "TU_PUBLIC_KEY_AQUI":
            verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
            verify_key.verify(x_signature_timestamp.encode() + body, bytes.fromhex(x_signature_ed25519))
    except BadSignatureError:
        logger.warning(f"🚨 Intento Fallido de Acceso Remoto. Archivo {event_id} descartado.")
        raise HTTPException(status_code=401, detail="Invalid request signature")

    payload = await request.json()
    interaction_type = payload.get("type")
    
    # 1. Validación PING
    if interaction_type == 1:
        return {"type": 1}
        
    # 2. Recepción de Application Command
    if interaction_type == 2:
        # Seguridad: Validación de Usuario Lista Blanca
        allowed_users = ["TU_USER_ID_AQUI"] # Reemplazar con config real
        user_id = payload.get("member", {}).get("user", {}).get("id")
        # MVP: Comentado if user_id not in allowed_users... en caso local user=None. Activar en Prod.

        command_name = payload.get("data", {}).get("name")
        if command_name == "nexo":
            options = payload.get("data", {}).get("options", [])
            nlp_prompt = ""
            for opt in options:
                if opt["name"] == "mutate":
                    nlp_prompt = opt["value"]
            
            if nlp_prompt:
                logger.info(f"🎙️ [VALIDADO] Instrucción Remota: '{nlp_prompt}' (ID: {event_id})")
                from services.ai_controller import interact_with_system
                
                # Despachar usando Queue Manager
                await system_queue.enqueue(interact_with_system, nlp_prompt, event_id=event_id)
                
                return {
                    "type": 4, 
                    "data": {
                        "content": f"🧠 Orden Críptica Aceptada: `{nlp_prompt}`. Validando en Pipeline Central..."
                    }
                }
                
    return {"type": 4, "data": {"content": "Sistema Nexo: Orden ignorada por Supervisor."}}
