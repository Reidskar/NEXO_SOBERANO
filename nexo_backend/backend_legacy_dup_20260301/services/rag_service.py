from nexo_v2 import NexoSoberano

class RAGService:

    def __init__(self):
        self.motor = NexoSoberano()

    def consultar(self, pregunta, categoria=None, mode="normal"):

        if mode == "fast":
            top_k = 3
            modelo = "flash"
        elif mode == "high":
            top_k = 8
            modelo = "pro"
        else:
            top_k = 5
            modelo = "flash"

        resultado = self.motor.consultar(
            pregunta=pregunta,
            categoria=categoria,
            top_k=top_k,
            modelo=modelo
        )

        return resultado
