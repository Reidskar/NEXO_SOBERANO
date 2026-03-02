"""Microsoft connector using Graph API to access OneDrive.

Relies on tokens from core/auth_manager.MicrosoftAuth.
"""
import logging
import requests

from core.auth_manager import get_microsoft_token

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

class MicrosoftConnector:
    def __init__(self):
        self.logger = logging.getLogger('MicrosoftConnector')
        self.token_data = {}
        self.headers = {}
        self._refresh_token()

    def _refresh_token(self):
        try:
            self.token_data = get_microsoft_token() or {}
            access_token = self.token_data.get('access_token')
            if not access_token:
                raise RuntimeError("Token sin access_token")
            self.headers = {'Authorization': f"Bearer {access_token}"}
        except Exception as e:
            self.logger.error("No fue posible obtener token de Microsoft: %s", e)
            self.token_data = {}
            self.headers = {}

    def _graph_get(self, endpoint: str, *, retry_on_401: bool = True):
        if not self.headers:
            self._refresh_token()
            if not self.headers:
                return []

        url = f"{GRAPH_BASE}{endpoint}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=30)
            if resp.status_code == 401 and retry_on_401:
                self.logger.info("Token Microsoft expirado/no válido; renovando e intentando de nuevo")
                self._refresh_token()
                if not self.headers:
                    return []
                resp = requests.get(url, headers=self.headers, timeout=30)

            resp.raise_for_status()
            return resp.json().get('value', [])
        except Exception as e:
            self.logger.error("Error en request Graph (%s): %s", endpoint, e)
            return []

    def _graph_request(self, endpoint: str, *, stream: bool = False, retry_on_401: bool = True):
        if not self.headers:
            self._refresh_token()
            if not self.headers:
                return None

        url = f"{GRAPH_BASE}{endpoint}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=60, stream=stream)
            if resp.status_code == 401 and retry_on_401:
                self.logger.info("Token Microsoft expirado/no válido; renovando e intentando de nuevo")
                self._refresh_token()
                if not self.headers:
                    return None
                resp = requests.get(url, headers=self.headers, timeout=60, stream=stream)

            resp.raise_for_status()
            return resp
        except Exception as e:
            self.logger.error("Error en request Graph (%s): %s", endpoint, e)
            return None

    def list_drive_root(self, top=20):
        """List items in the root of the signed-in user's OneDrive."""
        return self._graph_get(f"/me/drive/root/children?$top={top}")

    def list_recent_files(self, top=20):
        """Return recently modified Drive items."""
        return self._graph_get(f"/me/drive/recent?$top={top}")

    def download_file_content(self, item_id: str):
        """Download raw bytes from a OneDrive item id."""
        resp = self._graph_request(f"/me/drive/items/{item_id}/content", stream=False)
        if not resp:
            return None
        return resp.content

if __name__ == '__main__':
    conn = MicrosoftConnector()
    log.info(conn.list_drive_root())
    log.info(conn.list_recent_files())
