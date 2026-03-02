from fastapi import APIRouter, Request
from pydantic import BaseModel
from backend.services.omni_service import OmniChannelManager, TelegramAdapter
from backend.services.rag_service import RAGService

router = APIRouter(prefix="/omni", tags=["Omni"])

# la IA central puede ser la misma que usas para consultas
rag = RAGService()
manager = OmniChannelManager(ai_callback=lambda ch,txt: rag.consultar(pregunta=txt, categoria=None, mode="normal")["respuesta"])

# ejemplo de registro del adaptador telegram (token debe configurarse externamente)
# en producción guardar token en variables de entorno
TELEGRAM_TOKEN = ""  # rellena con tu token
if TELEGRAM_TOKEN:
    tg = TelegramAdapter(TELEGRAM_TOKEN, manager)
    manager.register_channel("telegram", tg.send)
    tg.start()

class SendRequest(BaseModel):
    channel: str
    to: str
    message: str

@router.post("/send")
def send(req: SendRequest):
    if req.channel in manager.handlers:
        manager.handlers[req.channel]["send"](req.to, req.message)
        return {"status": "sent"}
    return {"error": "unknown channel"}

@router.get("/diary")
def diary():
    return {"entries": manager.diary.get_all()}

# ruta para recibir webhooks genéricos (ej. Facebook, WhatsApp)
@router.post("/webhook/{channel}")
async def webhook(channel: str, request: Request):
    data = await request.json()
    # adaptar según el formato que venga
    sender = data.get("sender")
    text = data.get("message")
    manager.receive(channel, sender, text)
    return {"status": "ok"}
