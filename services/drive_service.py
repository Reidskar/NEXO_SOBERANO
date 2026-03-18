import os
import io
import logging
import asyncio
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from core.config import settings

logger = logging.getLogger(__name__)

class DriveService:
    def __init__(self):
        self.credentials_path = settings.GOOGLE_CREDENTIALS_PATH
        self.scopes = ['https://www.googleapis.com/auth/drive.readonly']
        self.service = self._build_service()

    def _build_service(self):
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            logger.warning("No Google Credentials found. DriveService is restricted.")
            return None
        try:
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.scopes
            )
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            logger.error(f"Error building Drive service: {e}")
            return None

    async def _run_in_thread(self, func, *args, **kwargs):
        """Previene bloquear el Event Loop con I/O de red de la API sincrónica"""
        return await asyncio.to_thread(func, *args, **kwargs)

    async def get_changes_since(self, folder_id: str, last_modified: datetime = None):
        """Sincronización incremental: recupera archivos modificados después de una fecha, con paginación."""
        if not self.service:
            logger.error("Drive API client is not initialized.")
            return []

        def _fetch():
            query = f"'{folder_id}' in parents and trashed=false"
            if last_modified:
                time_str = last_modified.isoformat() + "Z"
                query += f" and modifiedTime > '{time_str}'"
                
            results = []
            page_token = None
            while True:
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, createdTime, modifiedTime, mimeType, webViewLink)',
                    pageToken=page_token
                ).execute()
                
                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
            return results

        try:
            files = await self._run_in_thread(_fetch)
            logger.info(f"Drive API fetch: encontró {len(files)} archivos nuevos o modificados en {folder_id}.")
            return files
        except Exception as e:
            logger.error(f"Error fetching from Drive: {e}")
            return []

    async def download_file(self, file_id: str) -> bytes:
        """Descarga el contenido binario del archivo desde Drive"""
        if not self.service:
            return b""
            
        def _download():
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            return fh.getvalue()
            
        try:
            content = await self._run_in_thread(_download)
            return content
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return b""
            
drive_service = DriveService()
