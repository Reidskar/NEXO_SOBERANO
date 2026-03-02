from fastapi import APIRouter, Request, WebSocket
from pydantic import BaseModel
from backend.services.multi_ai_service import MultiAIService, AIProvider
from backend.services.conversation_service import ConversationService
from backend.services.omni_service import OmniChannelManager
from backend.services.rag_service import RAGService
import json

router = APIRouter(prefix="/chat", tags=["Chat"])

# Inicializar servicios
multi_ai = MultiAIService()
conv_service = ConversationService()
rag = RAGService()

# Callback inteligente que usa el contexto
def ai_callback(user_id: str, text: str) -> tuple[str, str]:
    """
    Callback central: recibe texto y devuelve (respuesta, modelo_usado)
    """
    # Agregar mensaje del usuario
    conv_service.add_message(user_id, "user", text, intent="chat")
    
    # Obtener histórico para contexto
    messages = conv_service.build_messages_for_model(user_id, limit=5)
    
    # Análisis cognitivo avant
    analysis = multi_ai.analyze(text, context=conv_service.get_summary(user_id))
    intent = analysis.get("intent", "chat")
    
    # Elegir proveedor según análisis o preferencia
    provider = AIProvider.AUTO
    pref = conv_service.get_user_preference(user_id, "ai_provider")
    if pref == "openai":
        provider = AIProvider.OPENAI
    elif pref == "gemini":
        provider = AIProvider.GEMINI
    
    # Obtener respuesta
    response, model_used = multi_ai.chat(messages, provider=provider)
    
    # Guardar respuesta en histórico
    conv_service.add_message(user_id, "assistant", response, model=model_used, intent=intent)
    
    # Actualizar contexto
    topic = analysis.get("topic", "general")
    conv_service.update_context(user_id, topic=topic)
    
    return response, model_used, intent, analysis

# Rutas REST
class ChatMessage(BaseModel):
    user_id: str
    text: str
    provider: str = "auto"  # "openai", "gemini", "auto"

@router.post("/send")
def send_message(msg: ChatMessage):
    """Envía un mensaje y obtiene respuesta."""
    response, model, intent, analysis = ai_callback(msg.user_id, msg.text)
    
    return {
        "response": response,
        "model_used": model,
        "intent": intent,
        "analysis": analysis,
        "timestamp": None
    }

@router.get("/history/{user_id}")
def get_history(user_id: str, limit: int = 20):
    """Obtiene historial del usuario."""
    return {"history": conv_service.get_conversation(user_id, limit=limit)}

@router.get("/context/{user_id}")
def get_context(user_id: str):
    """Obtiene contexto actual del usuario."""
    return {
        "context": conv_service.get_context(user_id),
        "summary": conv_service.get_summary(user_id)
    }

@router.post("/preference/{user_id}")
def set_preference(user_id: str, key: str, value: str):
    """Guarda preferencia del usuario."""
    conv_service.set_user_preference(user_id, key, value)
    return {"status": "saved"}

@router.post("/analyze")
def analyze(msg: ChatMessage):
    """Solo análisis cognitivo."""
    analysis = multi_ai.analyze(msg.text, context=conv_service.get_summary(msg.user_id))
    return {"analysis": analysis}

# WebSocket para chat en tiempo real (experimental)
@router.websocket("/ws/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response, model, intent, analysis = ai_callback(user_id, data)
            await websocket.send_json({
                "response": response,
                "model": model,
                "intent": intent
            })
    except Exception as e:
        log.info(f"WebSocket error: {e}")
