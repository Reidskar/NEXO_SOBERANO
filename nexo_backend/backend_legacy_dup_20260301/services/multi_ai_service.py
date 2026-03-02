"""
Multi-IA Service: Copilot (OpenAI) + Gemini (Google)
Abstracción unificada para usar ambos modelos o elegir dinámicamente.
"""

import os
from typing import Optional, List, Dict, Any
from enum import Enum

class AIProvider(Enum):
    OPENAI = "openai"      # Copilot
    GEMINI = "gemini"      # Google Gemini
    AUTO = "auto"          # elige el mejor según carga

class Message(Dict[str, str]):
    def __init__(self, role: str, content: str):
        super().__init__(role=role, content=content)

class MultiAIService:
    def __init__(
        self,
        openai_key: Optional[str] = None,
        gemini_key: Optional[str] = None,
    ):
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.gemini_key = gemini_key or os.getenv("GEMINI_API_KEY")
        
        if self.openai_key:
            try:
                import openai
                openai.api_key = self.openai_key
                self.openai_client = openai
            except ImportError:
                log.info("openai not installed")
                self.openai_client = None
        else:
            self.openai_client = None

        if self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self.gemini_client = genai
            except ImportError:
                log.info("google-generativeai not installed")
                self.gemini_client = None
        else:
            self.gemini_client = None

    def chat_openai(self, messages: List[Dict[str, str]], model: str = "gpt-4") -> str:
        """Usa OpenAI/Copilot"""
        if not self.openai_client:
            return "[OpenAI no configurado]"
        
        try:
            response = self.openai_client.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error OpenAI: {str(e)}"

    def chat_gemini(self, messages: List[Dict[str, str]]) -> str:
        """Usa Google Gemini"""
        if not self.gemini_client:
            return "[Gemini no configurado]"
        
        try:
            # Gemini usa distinto formato; convertir
            model = self.gemini_client.GenerativeModel("gemini-pro")
            text_content = " ".join([m["content"] for m in messages if m["role"] == "user"])
            response = model.generate_content(text_content)
            return response.text
        except Exception as e:
            return f"Error Gemini: {str(e)}"

    def chat(
        self,
        messages: List[Dict[str, str]],
        provider: AIProvider = AIProvider.AUTO,
        model: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Interface unificada.
        Retorna (respuesta, proveedor_usado)
        """
        if provider == AIProvider.AUTO:
            # elegir el mejor disponible (OpenAI primero)
            if self.openai_client:
                provider = AIProvider.OPENAI
            elif self.gemini_client:
                provider = AIProvider.GEMINI
            else:
                return "[Sin IA configurada]", "none"

        if provider == AIProvider.OPENAI:
            response = self.chat_openai(messages, model or "gpt-4")
            return response, "openai"
        elif provider == AIProvider.GEMINI:
            response = self.chat_gemini(messages)
            return response, "gemini"
        else:
            return "[Proveedor desconocido]", "none"

    def analyze(self, text: str, context: str = "") -> Dict[str, Any]:
        """
        Análisis cognitivo: intent, entities, sentiment, etc.
        """
        prompt = f"""
Analiza este texto y extrae:
- intent: qué quiere hacer (chat, enviar_mensaje, consultar, guardar, etc.)
- entidades: qué/quién se menciona (canales, usuarios, etc.)
- sentimiento: positivo/neutral/negativo
- acción: qué hacer a continuación

Texto: "{text}"
Contexto: {context}

Responde en JSON.
"""
        messages = [{"role": "user", "content": prompt}]
        response, _ = self.chat(messages)
        
        # intentar parsear como JSON
        try:
            import json
            return json.loads(response)
        except:
            return {"raw": response, "intent": "unknown"}
