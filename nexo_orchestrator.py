"""
Orquestador Maestro NEXO
Automatiza el inicio y monitoreo de todos los componentes del sistema
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _load_local_env(base_dir: Path) -> None:
    env_file = base_dir / ".env"
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


class ComponentStatus:
    """Estado de un componente del sistema"""
    def __init__(self, name: str):
        self.name = name
        self.running = False
        self.healthy = False
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[float] = None
        self.last_check: Optional[float] = None
        self.error_count = 0

    @property
    def uptime(self) -> float:
        if not self.start_time:
            return 0.0
        return time.time() - self.start_time

    def __repr__(self) -> str:
        status = "🟢" if self.healthy else ("🟡" if self.running else "🔴")
        uptime = f"{self.uptime:.0f}s" if self.running else "stopped"
        return f"{status} {self.name:20} [{uptime}]"


class NEXOOrchestrator:
    """Orquestador principal del sistema NEXO"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        _load_local_env(self.base_dir)
        self.components = {
            "obs": ComponentStatus("OBS Studio"),
            "backend": ComponentStatus("NEXO Backend"),
        }
        self.running = False
        self.obs_degraded_mode = (os.getenv("NEXO_OBS_DEGRADED_MODE", "true") or "true").strip().lower() in {"1", "true", "yes", "on"}
        self._obs_last_degraded_log = 0.0
        self._obs_degraded_log_interval = float((os.getenv("NEXO_OBS_DEGRADED_LOG_SECONDS", "60") or "60").strip())
        if self.obs_degraded_mode:
            for noisy_logger in (
                "obsws_python",
                "obsws_python.baseclient",
                "obsws_python.baseclient.ObsClient",
                "websocket",
                "websocket._http",
                "websocket._core",
            ):
                logging.getLogger(noisy_logger).setLevel(logging.CRITICAL)

    def _log_obs_degraded_once(self, detail: str = "") -> None:
        now = time.time()
        if now - self._obs_last_degraded_log < self._obs_degraded_log_interval:
            return
        self._obs_last_degraded_log = now
        extra = f" ({detail})" if detail else ""
        logger.info("ℹ️ OBS no disponible%s — continuando en modo degradado limpio", extra)

    async def check_obs_websocket(self) -> bool:
        """Verifica si OBS WebSocket está disponible"""
        try:
            from obsws_python import ReqClient
            obs_host = (os.getenv("OBS_HOST", "localhost") or "localhost").strip()
            obs_port = int((os.getenv("OBS_PORT", "4455") or "4455").strip())
            obs_password = (os.getenv("OBS_PASSWORD", "") or "").strip()
            client = ReqClient(host=obs_host, port=obs_port, password=obs_password, timeout=3)
            client.get_version()
            return True
        except Exception:
            return False

    async def check_backend_health(self) -> bool:
        """Verifica si el backend NEXO está saludable"""
        try:
            async with aiohttp.ClientSession() as session:
                api_key = (os.getenv("NEXO_API_KEY", "") or "").strip()
                headers = {"X-NEXO-KEY": api_key} if api_key else {}
                async with session.get(
                    "http://localhost:8080/api/health",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as response:
                    return response.status == 200
        except Exception:
            return False

    async def start_obs(self) -> bool:
        """Inicia OBS Studio"""
        comp = self.components["obs"]
        
        # Buscar OBS en ubicaciones comunes
        obs_paths = []
        obs_exe_env = (os.getenv("OBS_EXE_PATH", "") or "").strip()
        if obs_exe_env:
            obs_paths.append(obs_exe_env)
        obs_paths.extend([
            r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
            r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
        ])
        
        obs_exe = None
        for path in obs_paths:
            if Path(path).exists():
                obs_exe = path
                break
        
        if not obs_exe:
            logger.error("OBS Studio no encontrado en ubicaciones estándar")
            return False

        obs_bin_dir = str(Path(obs_exe).parent)
        obs_root_dir = Path(obs_exe).parents[2]
        locale_file = obs_root_dir / "data" / "obs-studio" / "locale" / "en-US.ini"
        if not locale_file.exists():
            logger.error("OBS locale faltante: %s", locale_file)
            return False

        try:
            # Iniciar OBS minimizado
            comp.process = subprocess.Popen(
                [obs_exe, "--minimize-to-tray"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=obs_bin_dir,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            comp.running = True
            comp.start_time = time.time()
            logger.info("OBS Studio iniciado (minimizado)")
            
            # Esperar a que el WebSocket esté disponible
            for _ in range(10):
                await asyncio.sleep(1)
                if await self.check_obs_websocket():
                    comp.healthy = True
                    logger.info("✅ OBS WebSocket disponible")
                    return True
            
            logger.warning("⚠️ OBS iniciado pero WebSocket no responde")
            return False
            
        except Exception as exc:
            logger.error(f"Error iniciando OBS: {exc}")
            comp.error_count += 1
            return False

    async def start_backend(self) -> bool:
        """Inicia el backend NEXO"""
        comp = self.components["backend"]
        
        try:
            python_exe = sys.executable
            backend_script = self.base_dir / "run_backend.py"
            
            if not backend_script.exists():
                logger.error(f"Script backend no encontrado: {backend_script}")
                return False

            comp.process = subprocess.Popen(
                [python_exe, str(backend_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.base_dir),
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            comp.running = True
            comp.start_time = time.time()
            logger.info("Backend NEXO iniciado")
            
            # Esperar a que el backend esté saludable
            for _ in range(15):
                await asyncio.sleep(1)
                if await self.check_backend_health():
                    comp.healthy = True
                    logger.info("✅ Backend NEXO saludable")
                    return True
            
            logger.warning("⚠️ Backend iniciado pero no responde health checks")
            return False
            
        except Exception as exc:
            logger.error(f"Error iniciando backend: {exc}")
            comp.error_count += 1
            return False

    async def monitor_components(self) -> None:
        """Monitorea continuamente el estado de los componentes"""
        while self.running:
            try:
                # Verificar OBS
                if self.components["obs"].running:
                    self.components["obs"].healthy = await self.check_obs_websocket()
                    self.components["obs"].last_check = time.time()
                
                # Verificar Backend
                if self.components["backend"].running:
                    self.components["backend"].healthy = await self.check_backend_health()
                    self.components["backend"].last_check = time.time()
                
                # Reiniciar componentes no saludables
                for name, comp in self.components.items():
                    if comp.running and not comp.healthy:
                        comp.error_count += 1
                        if name == "obs" and self.obs_degraded_mode:
                            self._log_obs_degraded_once("monitor")
                            continue
                        if comp.error_count >= 5:
                            logger.error(f"❌ {name} no responde - reiniciando...")
                            await self.restart_component(name)
                
                await asyncio.sleep(10)  # Check cada 10 segundos
                
            except Exception as exc:
                logger.error(f"Error en monitoreo: {exc}")
                await asyncio.sleep(5)

    async def restart_component(self, name: str) -> bool:
        """Reinicia un componente específico"""
        comp = self.components.get(name)
        if not comp:
            return False

        logger.info(f"Reiniciando {name}...")
        
        # Detener componente
        if comp.process:
            try:
                comp.process.terminate()
                comp.process.wait(timeout=5)
            except Exception:
                comp.process.kill()
        
        comp.running = False
        comp.healthy = False
        comp.error_count = 0
        await asyncio.sleep(2)
        
        # Reiniciar componente
        if name == "obs":
            return await self.start_obs()
        elif name == "backend":
            return await self.start_backend()
        
        return False

    async def start_all(self) -> bool:
        """Inicia todos los componentes del sistema"""
        logger.info("=" * 60)
        logger.info("  🚀 NEXO Orquestador - Iniciando Sistema")
        logger.info("=" * 60)
        
        self.running = True
        
        # 1. Verificar e iniciar OBS
        logger.info("\n📡 Paso 1: Iniciando OBS Studio...")
        if not await self.check_obs_websocket():
            started = await self.start_obs()
            if not started and self.obs_degraded_mode:
                self.components["obs"].running = False
                self.components["obs"].healthy = False
                self._log_obs_degraded_once("startup")
        else:
            logger.info("✅ OBS ya está ejecutándose")
            self.components["obs"].running = True
            self.components["obs"].healthy = True
            self.components["obs"].start_time = time.time()
        
        await asyncio.sleep(2)
        
        # 2. Iniciar Backend
        logger.info("\n🔧 Paso 2: Iniciando Backend NEXO...")
        if not await self.check_backend_health():
            await self.start_backend()
        else:
            logger.info("✅ Backend ya está ejecutándose")
            self.components["backend"].running = True
            self.components["backend"].healthy = True
            self.components["backend"].start_time = time.time()
        
        # 3. Status final
        logger.info("\n" + "=" * 60)
        logger.info("  📊 Estado del Sistema")
        logger.info("=" * 60)
        for comp in self.components.values():
            logger.info(f"  {comp}")
        
        all_healthy = all(c.healthy for c in self.components.values())
        if self.obs_degraded_mode and self.components["backend"].healthy:
            # Permite operación útil aunque OBS no esté arriba.
            all_healthy = True
        
        if all_healthy:
            logger.info("\n✨ Sistema completamente operacional")
            logger.info("🌐 Panel de control: http://localhost:8080/api/docs")
            logger.info("🎮 Control de stream disponible via API")
        else:
            logger.warning("\n⚠️ Sistema iniciado con advertencias")
        
        logger.info("=" * 60)
        
        return all_healthy

    async def shutdown(self) -> None:
        """Detiene todos los componentes de forma ordenada"""
        logger.info("\n🛑 Deteniendo sistema NEXO...")
        self.running = False
        
        for name, comp in self.components.items():
            if comp.process:
                logger.info(f"Deteniendo {name}...")
                try:
                    comp.process.terminate()
                    comp.process.wait(timeout=5)
                except Exception:
                    comp.process.kill()
                comp.running = False
                comp.healthy = False
        
        logger.info("✅ Sistema detenido")

    async def run(self) -> None:
        """Ejecuta el orquestador completo"""
        try:
            await self.start_all()
            
            # Iniciar monitoreo en background
            monitor_task = asyncio.create_task(self.monitor_components())
            
            logger.info("\n👀 Monitoreo activo (Ctrl+C para detener)\n")
            
            # Mantener el script ejecutándose
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n\n🛑 Interrupción recibida")
        finally:
            await self.shutdown()


async def main():
    """Función principal"""
    orchestrator = NEXOOrchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
