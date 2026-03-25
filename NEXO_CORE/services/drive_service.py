"""
NEXO SOBERANO — Drive Service
Acceso a Google Drive para lectura y búsqueda de archivos.
"""
from __future__ import annotations
import logging
import os
from typing import Optional

logger = logging.getLogger("NEXO.services.drive")

GEOPOLITICA_FOLDER_ID = os.getenv(
    "GOOGLE_DRIVE_FOLDER_ID_GEOPOLITICA",
    "10pn6Zo5_SUTf2jlWaH98rs0wtF3W0Trx"
)


class DriveService:
    def __init__(self):
        self.service = None
        self._init_service()

    def _init_service(self):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds_path = os.getenv(
                "GOOGLE_CREDENTIALS_PATH",
                "credenciales_google.json"
            )
            if not os.path.exists(creds_path):
                logger.warning(f"Drive: credenciales no encontradas en {creds_path}")
                return

            scopes = ["https://www.googleapis.com/auth/drive.readonly"]
            creds = service_account.Credentials.from_service_account_file(
                creds_path, scopes=scopes
            )
            self.service = build("drive", "v3", credentials=creds, cache_discovery=False)
            logger.info("Drive Service inicializado correctamente.")
        except Exception as e:
            logger.warning(f"Drive Service no disponible: {e}")

    async def listar_archivos_carpeta(
        self,
        folder_id: str = GEOPOLITICA_FOLDER_ID,
        max_results: int = 50
    ) -> list[dict]:
        """Lista archivos de una carpeta de Drive."""
        try:
            if not self.service:
                return []
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                pageSize=max_results,
                fields="files(id,name,mimeType,modifiedTime,size)"
            ).execute()
            return results.get("files", [])
        except Exception as e:
            logger.error(f"Error listando Drive: {e}")
            return []

    async def leer_archivo_texto(self, file_id: str) -> str:
        """Lee contenido de texto de un archivo Drive."""
        try:
            if not self.service:
                return ""
            file_meta = self.service.files().get(
                fileId=file_id,
                fields="mimeType,name"
            ).execute()
            mime = file_meta.get("mimeType", "")

            if "google-apps.document" in mime:
                content = self.service.files().export(
                    fileId=file_id,
                    mimeType="text/plain"
                ).execute()
                return content.decode("utf-8") if isinstance(content, bytes) else content
            elif mime.startswith("text/"):
                content = self.service.files().get_media(
                    fileId=file_id
                ).execute()
                return content.decode("utf-8") if isinstance(content, bytes) else str(content)
            else:
                return f"[Archivo binario: {file_meta.get('name')}]"
        except Exception as e:
            logger.error(f"Error leyendo archivo {file_id}: {e}")
            return ""

    async def buscar_en_drive(
        self,
        query: str,
        folder_id: str = GEOPOLITICA_FOLDER_ID
    ) -> list[dict]:
        """Búsqueda de texto en Drive."""
        try:
            if not self.service:
                return []
            safe_query = query.replace("'", "\\'")
            results = self.service.files().list(
                q=f"fullText contains '{safe_query}' and '{folder_id}' in parents and trashed=false",
                pageSize=10,
                fields="files(id,name,mimeType,modifiedTime)"
            ).execute()
            return results.get("files", [])
        except Exception as e:
            logger.error(f"Error buscando en Drive: {e}")
            return []


drive_service = DriveService()
