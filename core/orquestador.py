"""Central controller coordinating core intelligence workflows.

Includes cost management, decision engine, and high-level orchestration.
This is the updated Orquestador Central described in the strategic update.
"""
import os
import sys
from datetime import datetime

# ensure project root is on path so we can import services
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

class GestorDeCostos:
    """Controla el presupuesto y evita llamadas innecesarias a la API (Punto 6)"""
    def __init__(self):
        self.presupuesto_diario = 1000000  # Límite de tokens diarios
        self.tokens_usados_hoy = 0

    def registrar_gasto(self, tokens, modelo="gemini"):
        self.tokens_usados_hoy += tokens
        # Aquí iría el guardado en base de datos de auditoría
        log.info(f"💰 [FINANZAS] Consumo registrado: {tokens} tokens. Total hoy: {self.tokens_usados_hoy}")

    def puede_operar(self):
        return self.tokens_usados_hoy < self.presupuesto_diario

class MotorDeDecision:
    """Evalúa qué hacer con cada pieza de inteligencia (Punto 3)"""
    def evaluar_importancia(self, metadatos_archivo):
        # Lógica simulada: Si el archivo viene de una fuente prioritaria o tiene palabras clave
        fuentes_alta_prioridad = ["OTAN", "MiddleEast", "Economia_Austriaca", "Latam"]
        
        for fuente in fuentes_alta_prioridad:
            if fuente.lower() in metadatos_archivo.lower():
                return "ALTA_PRIORIDAD"
        return "RUTINA"

from services.connectors.google_connector import GoogleConnector
from services.connectors.microsoft_connector import MicrosoftConnector

class OrquestadorCentral:
    """El cerebro que coordina todo (Punto 1)"""
    def __init__(self):
        self.finanzas = GestorDeCostos()
        self.estrategia = MotorDeDecision()
        # initialize connectors
        try:
            self.google = GoogleConnector()
        except Exception as e:
            log.info(f"⚠️ No se pudo inicializar GoogleConnector: {e}")
            self.google = None
        try:
            self.microsoft = MicrosoftConnector()
        except Exception:
            self.microsoft = None

    def procesar_nuevo_archivo(self, ruta_archivo, nombre_archivo):
        log.info(f"\n⚙️ [ORQUESTADOR] Recibiendo nueva inteligencia: {nombre_archivo}")
        
        if not self.finanzas.puede_operar():
            log.info("🛑 [ALERTA] Presupuesto diario agotado. Encolando para mañana.")
            return

        # 1. Decisión Estratégica
        prioridad = self.estrategia.evaluar_importancia(ruta_archivo)
        log.info(f"🎯 [ESTRATEGIA] Nivel de prioridad asignado: {prioridad}")

        # 2. Enrutamiento Inteligente
        if prioridad == "ALTA_PRIORIDAD":
            log.info("🚀 [ACCIÓN] Enviando a Gemini Pro para análisis exhaustivo y generación de guion para YouTube...")
            # Aquí llamaremos a services.intelligence.py
            self.finanzas.registrar_gasto(1500, "gemini")
            self.generar_pipeline_contenido(nombre_archivo)
            
        else:
            log.info("🔍 [ACCIÓN] Procesando con Modelo Local (Costo Cero) solo para indexación básica...")
            # Aquí llamaremos a un modelo local (ej. sentence-transformers)
            self.finanzas.registrar_gasto(0, "local")

    def generar_pipeline_contenido(self, tema):
        """Pipeline de automatización (Punto 7)"""
        log.info(f"📢 [PIPELINE] Generando ruta de reciclaje para: {tema}")
        log.info("   -> 1. Extrayendo puntos clave para Discord.")
        log.info("   -> 2. Redactando borrador de Hilo para X/Twitter.")
        log.info("   -> 3. Agendando revisión en Notion para próximo directo.")

    def sincronizar_conectores(self):
        """Obtener archivos recientes de conectores y procesarlos."""
        if self.google:
            log.info("🔄 Sincronizando con Google Drive/Photos...")
            try:
                drive_files = self.google.list_drive_files()
                for f in drive_files:
                    nombre = f.get('name')
                    self.procesar_nuevo_archivo(f.get('id', ''), nombre)
            except Exception as e:
                log.info(f"⚠️ Falló sync Google Drive: {e}")

            try:
                photo_items = self.google.list_photos()
                for p in photo_items:
                    nombre = p.get('filename', 'photo')
                    self.procesar_nuevo_archivo(p.get('id', ''), nombre)
            except Exception as e:
                log.info(f"⚠️ Falló sync Google Photos: {e}")
        if self.microsoft:
            log.info("🔄 Sincronizando con OneDrive...")
            try:
                files = self.microsoft.list_recent_files()
                for f in files:
                    nombre = f.get('name')
                    self.procesar_nuevo_archivo(f.get('id', ''), nombre)
            except Exception as e:
                log.info(f"⚠️ Falló sync OneDrive: {e}")

# --- PRUEBA TÁCTICA ---
if __name__ == "__main__":
    jarvis = OrquestadorCentral()
    log.info("🤖 JARVIS: Orquestador Central en línea. Esperando órdenes, Director.")
    
    # sincronizar conectores (si hay credenciales válidas)
    jarvis.sincronizar_conectores()
    
    # también podemos simular entradas manuales
    jarvis.procesar_nuevo_archivo("C:/Drive/Entrada/reporte_OTAN_2026.pdf", "reporte_OTAN_2026.pdf")
    jarvis.procesar_nuevo_archivo("C:/Drive/Entrada/recibo_luz_enero.jpg", "recibo_luz_enero.jpg")