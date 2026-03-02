class NexoSoberano:
    def __init__(self):
        self._ready = True

    def consultar(self, pregunta, categoria=None, top_k=5, modelo="flash"):
        respuesta = f"[MODELO:{modelo}] Respuesta estratégica a: {pregunta}"
        fuentes = [
            {"titulo": "Documento Interno 1", "score": 0.92},
            {"titulo": "Documento Interno 2", "score": 0.87},
        ]

        tokens = len(pregunta) // 2 + 120

        return {
            "respuesta": respuesta,
            "fuentes": fuentes[:top_k],
            "tokens_reales": tokens,
            "modelo_usado": modelo
        }
