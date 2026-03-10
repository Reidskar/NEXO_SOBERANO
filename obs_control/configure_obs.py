"""
Configurador Automático de OBS
Configura OBS Studio profesionalmente usando el perfil NEXO
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from obsws_python import ReqClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_local_env() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return
    try:
        for raw_line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    except Exception as exc:
        logger.debug("No se pudo cargar .env local: %s", exc)


_load_local_env()


def _obs_password_from_env() -> str:
    return (os.getenv("OBS_PASSWORD", "") or "").strip()


def _scene_names(scene_list_response: Any) -> list[str]:
    scenes = getattr(scene_list_response, "scenes", None) or []
    names: list[str] = []
    for scene in scenes:
        try:
            names.append(str(scene.get("sceneName", "")))
        except Exception:
            continue
    return [name for name in names if name]


class OBSConfigurator:
    """Configura OBS automáticamente desde un perfil JSON"""

    def __init__(self, host: str = "localhost", port: int = 4455, password: str = ""):
        self.host = host
        self.port = port
        self.password = password
        self.client: Optional[ReqClient] = None

    def connect(self) -> bool:
        """Conecta al servidor WebSocket de OBS"""
        try:
            self.client = ReqClient(host=self.host, port=self.port, password=self.password, timeout=10)
            last_exc: Optional[Exception] = None
            for _ in range(12):
                try:
                    self.client.get_scene_list()
                    break
                except Exception as exc:
                    last_exc = exc
                    if "not ready" in str(exc).lower():
                        time.sleep(0.5)
                        continue
                    raise
            else:
                if last_exc:
                    raise last_exc
            logger.info(f"Conectado a OBS en {self.host}:{self.port}")
            return True
        except Exception as exc:
            logger.error(f"Error conectando a OBS: {exc}")
            return False

    def disconnect(self) -> None:
        """Desconecta del servidor WebSocket """
        if self.client:
            try:
                self.client.disconnect()
                logger.info("Desconectado de OBS")
            except Exception:
                pass

    def load_profile(self, profile_path: str) -> Optional[Dict[str, Any]]:
        """Carga el perfil desde archivo JSON"""
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
            logger.info(f"Perfil cargado: {profile['profile']['name']}")
            return profile
        except Exception as exc:
            logger.error(f"Error cargando perfil: {exc}")
            return None

    def create_scene(self, scene_name: str) -> bool:
        """Crea una nueva escena en OBS"""
        if not self.client:
            return False
        
        try:
            # Verifica si la escena ya existe
            scenes = self.client.get_scene_list()
            existing = _scene_names(scenes)
            
            if scene_name in existing:
                logger.info(f"Escena '{scene_name}' ya existe")
                return True
            
            self.client.create_scene(scene_name)
            logger.info(f"Escena creada: {scene_name}")
            return True
        except Exception as exc:
            logger.error(f"Error creando escena {scene_name}: {exc}")
            return False

    def create_text_source(
        self,
        scene_name: str,
        source_name: str,
        text: str,
        font_face: str = "Arial",
        font_size: int = 48,
        color: int = 0xFFFFFFFF
    ) -> bool:
        """Crea una fuente de texto en una escena"""
        if not self.client:
            return False

        try:
            settings = {
                "text": text,
                "font": {
                    "face": font_face,
                    "size": font_size,
                    "style": "Bold"
                },
                "color": color,
                "outline": True,
                "outline_size": 2,
                "outline_color": 0xFF000000
            }

            input_kinds = [
                "text_ft2_source_v2",
                "text_ft2_source",
                "text_gdiplus_v2",
                "text_gdiplus",
            ]

            for kind in input_kinds:
                try:
                    self.client.create_input(
                        sceneName=scene_name,
                        inputName=source_name,
                        inputKind=kind,
                        inputSettings=settings,
                        sceneItemEnabled=True
                    )
                    logger.info(f"Fuente de texto creada: {source_name} en {scene_name} ({kind})")
                    return True
                except Exception as exc:
                    if "already exists" in str(exc).lower():
                        logger.info(f"Fuente de texto ya existe: {source_name} en {scene_name}")
                        return True
                    continue

            logger.error(
                "Error creando fuente de texto %s en %s: ningún inputKind soportado (%s)",
                source_name,
                scene_name,
                ", ".join(input_kinds),
            )
            return False
        except Exception as exc:
            logger.error(f"Error creando fuente de texto: {exc}")
            return False

    def create_color_source(
        self,
        scene_name: str,
        source_name: str,
        color: int = 0xFF000000,
        width: int = 1920,
        height: int = 1080
    ) -> bool:
        """Crea una fuente de color (fondo) en una escena"""
        if not self.client:
            return False

        try:
            settings = {
                "color": color,
                "width": width,
                "height": height
            }

            self.client.create_input(
                sceneName=scene_name,
                inputName=source_name,
                inputKind="color_source_v3",
                inputSettings=settings,
                sceneItemEnabled=True
            )
            logger.info(f"Fuente de color creada: {source_name} en {scene_name}")
            return True
        except Exception as exc:
            if "already exists" in str(exc).lower():
                logger.info(f"Fuente de color ya existe: {source_name} en {scene_name}")
                return True
            logger.error(f"Error creando fuente de color: {exc}")
            return False

    def configure_from_profile(self, profile: Dict[str, Any]) -> bool:
        """Configura OBS usando el perfil completo"""
        if not self.client:
            logger.error("Cliente no conectado")
            return False

        success = True

        # Crear escenas del perfil
        for scene_config in profile.get("scenes", []):
            scene_name = scene_config["name"]
            if not self.create_scene(scene_name):
                success = False
                continue

            # Crear fuentes en la escena
            for source in scene_config.get("sources", []):
                source_type = source["type"]
                source_name = source["name"]
                settings = source.get("settings", {})

                try:
                    if source_type == "text_gdiplus_v2":
                        text = settings.get("text", "")
                        font = settings.get("font", {})
                        color = settings.get("color", 0xFFFFFFFF)
                        
                        self.create_text_source(
                            scene_name,
                            source_name,
                            text,
                            font.get("face", "Arial"),
                            font.get("size", 48),
                            color
                        )
                    
                    elif source_type == "color_source":
                        color = settings.get("color", 0xFF000000)
                        width = settings.get("width", 1920)
                        height = settings.get("height", 1080)
                        
                        self.create_color_source(
                            scene_name,
                            source_name,
                            color,
                            width,
                            height
                        )
                    
                    elif source_type == "display_capture":
                        # Display capture es específico de plataforma
                        logger.info(f"Captura de pantalla debe configurarse manualmente: {source_name}")
                
                except Exception as exc:
                    logger.error(f"Error configurando fuente {source_name}: {exc}")
                    success = False

        return success

    def set_current_scene(self, scene_name: str) -> bool:
        """Establece la escena actual"""
        if not self.client:
            return False

        try:
            self.client.set_current_program_scene(scene_name)
            logger.info(f"Escena actual establecida: {scene_name}")
            return True
        except Exception as exc:
            logger.error(f"Error estableciendo escena: {exc}")
            return False

    def get_scenes(self) -> list[str]:
        """Obtiene la lista de escenas disponibles"""
        if not self.client:
            return []

        try:
            scenes = self.client.get_scene_list()
            return _scene_names(scenes)
        except Exception as exc:
            logger.error(f"Error obteniendo escenas: {exc}")
            return []

    def apply_professional_profile(self) -> bool:
        """Aplica el perfil profesional completo"""
        profile_path = Path(__file__).parent / "obs_professional_profile.json"
        
        if not profile_path.exists():
            logger.error(f"Perfil no encontrado: {profile_path}")
            return False

        profile = self.load_profile(str(profile_path))
        if not profile:
            return False

        if not self.connect():
            return False

        try:
            success = self.configure_from_profile(profile)
            
            if success:
                # Establece la primera escena como actual
                scenes = profile.get("scenes", [])
                if scenes:
                    self.set_current_scene(scenes[0]["name"])
                
                logger.info("✅ Perfil profesional aplicado con éxito")
            else:
                logger.warning("⚠️ Perfil aplicado con algunos errores")
            
            return success
        finally:
            self.disconnect()


def main():
    """Función principal para ejecutar el configurador"""
    logger.info("=" * 60)
    logger.info("  NEXO OBS Configurador Profesional")
    logger.info("=" * 60)
    print()

    configurator = OBSConfigurator(
        host="localhost",
        port=4455,
        password=_obs_password_from_env()
    )

    logger.info("📡 Conectando a OBS...")
    if not configurator.connect():
        logger.info("❌ No se pudo conectar a OBS")
        logger.info("   Asegúrate de que OBS está ejecutándose y WebSocket habilitado")
        return

    logger.info("✅ Conectado a OBS")
    print()
    logger.info("📋 Escenas actuales:")
    scenes = configurator.get_scenes()
    for i, scene in enumerate(scenes, 1):
        logger.info(f"   {i}. {scene}")
    print()

    logger.info("🔧 Aplicando perfil profesional...")
    configurator.disconnect()  # Desconectar para aplicar desde cero
    
    if configurator.apply_professional_profile():
        logger.info("✅ Configuración completada")
        print()
        logger.info("🎬 Escenas profesionales creadas:")
        logger.info("   - Escena Principal (con overlay)")
        logger.info("   - Escena BRB (volveremos pronto)")
        logger.info("   - Escena Final (gracias por ver)")
        print()
        logger.info("🎮 Hotkeys configurados (configura manualmente en OBS):")
        logger.info("   F9  - Iniciar Stream")
        logger.info("   F10 - Detener Stream")
        logger.info("   F11 - Iniciar Grabación")
        logger.info("   F12 - Detener Grabación")
    else:
        logger.info("⚠️ La configuración se completó con algunos errores")
    
    print()
    logger.info("✨ Usa NEXO Backend para controlar OBS remotamente")


if __name__ == "__main__":
    main()
