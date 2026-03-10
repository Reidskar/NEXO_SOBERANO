import os
import json
import io
import logging
import mimetypes
import requests
from pathlib import Path
from typing import Optional, Dict, Any, Union
from google.oauth2.credentials import Credentials
from google.auth.external_account_authorized_user import Credentials as ExternalAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

logger = logging.getLogger(__name__)


def _resolve_auth_dir() -> Path:
    env_auth_dir = os.getenv("NEXO_AUTH_DIR")
    if env_auth_dir:
        return Path(env_auth_dir)

    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "backend" / "auth"
        if candidate.exists():
            return candidate

    return current.parent.parent.parent / "backend" / "auth"


AUTH_DIR = _resolve_auth_dir()
BASE_DIR = AUTH_DIR.parent.parent
DRIVE_CLIENT_SECRETS_FILE = AUTH_DIR / "drive_client_secrets.json"

# make sure auth directory exists
AUTH_DIR.mkdir(parents=True, exist_ok=True)

SCOPES_DRIVE = [
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
]

SCOPES_DRIVE_MANAGE = [
    'https://www.googleapis.com/auth/drive',
]

SCOPES_FULL = [
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/photoslibrary',
    'https://www.googleapis.com/auth/photoslibrary.readonly',
]

SCOPES_MANAGE_FULL = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/photoslibrary',
    'https://www.googleapis.com/auth/photoslibrary.readonly',
]


def create_drive_client_secrets_from_env() -> Path:
    """Create Drive OAuth client secrets file from environment variables.

    Required env vars:
    - DRIVE_CLIENT_ID
    - DRIVE_CLIENT_SECRET
    """
    client_id = os.getenv("DRIVE_CLIENT_ID", "").strip() or os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("DRIVE_CLIENT_SECRET", "").strip() or os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise ValueError("Faltan DRIVE_CLIENT_ID/DRIVE_CLIENT_SECRET o GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET en entorno/.env")

    project_id = os.getenv("DRIVE_PROJECT_ID", "nexo-soberano-drive")
    payload = {
        "installed": {
            "client_id": client_id,
            "project_id": project_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"],
        }
    }

    DRIVE_CLIENT_SECRETS_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return DRIVE_CLIENT_SECRETS_FILE


def _resolve_google_credentials_file(require_drive_write: bool = False) -> Path:
    if require_drive_write:
        if DRIVE_CLIENT_SECRETS_FILE.exists():
            return DRIVE_CLIENT_SECRETS_FILE
        if os.getenv("DRIVE_CLIENT_ID") and os.getenv("DRIVE_CLIENT_SECRET"):
            try:
                return create_drive_client_secrets_from_env()
            except Exception as exc:
                logger.warning("No fue posible crear credenciales de Drive desde entorno: %s", exc)

    credentials_path = AUTH_DIR / "credenciales_google.json"
    if credentials_path.exists():
        return credentials_path

    alt_root = BASE_DIR / "credenciales_google.json"
    if alt_root.exists():
        return alt_root

    desktop_file = Path.home() / "Desktop" / "credenciales_google.json"
    if desktop_file.exists():
        return desktop_file

    downloads_file = Path.home() / "Downloads" / "credenciales_google.json"
    if downloads_file.exists():
        return downloads_file

    for f in (Path.home() / "Downloads").glob('client_secret_*.json'):
        return f

    return AUTH_DIR / "credenciales_google.json"


def get_google_credentials(require_photos: bool = False, require_drive_write: bool = False, allow_interactive: bool = False) -> Union[Credentials, ExternalAccountCredentials]:
    creds = None
    if require_drive_write and require_photos:
        token_name = "token_google_manage_full.json"
    elif require_drive_write:
        token_name = "token_google_manage.json"
    elif require_photos:
        token_name = "token_google_full.json"
    else:
        token_name = "token_google_drive.json"

    token_path = AUTH_DIR / token_name
    legacy_token_path = AUTH_DIR / "token_google.json"
    credentials_path = _resolve_google_credentials_file(require_drive_write=require_drive_write)
    if require_drive_write and require_photos:
        scopes = SCOPES_MANAGE_FULL
    elif require_drive_write:
        scopes = SCOPES_DRIVE_MANAGE
    elif require_photos:
        scopes = SCOPES_FULL
    else:
        scopes = SCOPES_DRIVE

    alt_root = BASE_DIR / "credenciales_google.json"

    if not credentials_path.exists():
        desktop = Path.home() / "Desktop"
        desktop_file = desktop / "credenciales_google.json"
        if desktop_file.exists():
            import shutil
            shutil.copy(desktop_file, credentials_path)
            logger.info("Copiada credencial de Google desde Escritorio: %s", credentials_path)

    if credentials_path.exists():
        txt = credentials_path.read_text(errors='ignore')
        if 'YOUR_CLIENT_ID' in txt or 'YOUR_CLIENT_SECRET' in txt:
            logger.warning("Credencial placeholder detectada; eliminando archivo inválido: %s", credentials_path)
            credentials_path.unlink()

    downloads = Path.home() / "Downloads"
    dl_file = downloads / "credenciales_google.json"
    if dl_file.exists() and not credentials_path.exists():
        import shutil
        shutil.copy(dl_file, credentials_path)
        logger.info("Copiada credencial de Google desde Descargas: %s", credentials_path)

    if not credentials_path.exists():
        for f in downloads.glob('client_secret_*.json'):
            try:
                import shutil
                shutil.copy(f, credentials_path)
                logger.info("Copiada credencial de Google desde %s a %s", f.name, credentials_path.name)
                break
            except Exception as exc:
                logger.debug("No fue posible copiar credencial alternativa %s: %s", f, exc)

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), scopes)
            if creds and hasattr(creds, "has_scopes") and not creds.has_scopes(scopes):
                logger.warning("Token en %s no contiene scopes requeridos, solicitando reautorización", token_path)
                creds = None
        except Exception as exc:
            logger.warning("Token de Google inválido en %s: %s", token_path, exc)
            creds = None
    elif legacy_token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(legacy_token_path), scopes)
            if creds and hasattr(creds, "has_scopes") and not creds.has_scopes(scopes):
                logger.warning("Token legacy en %s no contiene scopes requeridos", legacy_token_path)
                creds = None
        except Exception as exc:
            logger.debug("No se pudo usar token legacy de Google %s: %s", legacy_token_path, exc)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                logger.warning("Falló refresh de token Google: %s", exc)
                creds = None

        if not creds or not creds.valid:
            if not allow_interactive:
                scope_label = "drive" if require_drive_write else "drive.readonly"
                if require_photos:
                    scope_label = f"{scope_label}+photos"
                raise RuntimeError(
                    f"Token Google no disponible para scope {scope_label}. "
                    "Autoriza previamente de forma interactiva y reintenta."
                )

            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"No se encontró credenciales de Google. "
                    f"Coloca el archivo en {credentials_path} o en {alt_root}"
                )
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), scopes
                )
                creds = flow.run_local_server(port=0)
            except Exception as e:
                msg = str(e)
                if require_photos and ("access_denied" in msg or "Error 403" in msg):
                    raise RuntimeError(
                        "Google Photos bloqueado por verificación OAuth (Error 403 access_denied). "
                        "Agrega tu correo como usuario de prueba en Google Cloud o publica/verifica la app."
                    )
                logger.error("Error iniciando OAuth con Google: %s", e)
                raise RuntimeError(
                    f"Error iniciando OAuth con Google: {e}. "
                    "Revisa que el archivo de credenciales contenga valores reales."
                )

        if creds:
            with open(token_path, "w") as token:
                token.write(creds.to_json())

    return creds


def get_drive_service():
    """Return an authenticated Google Drive service object.

    Credentials are stored in backend/auth/token_google.json and the
    client secrets file must be at backend/auth/credenciales_google.json.
    """
    creds = get_google_credentials(require_photos=False, allow_interactive=False)
    return build("drive", "v3", credentials=creds)


def get_drive_manage_service():
    """Drive service with write permissions for organizing files and uploads."""
    creds = get_google_credentials(require_photos=False, require_drive_write=True, allow_interactive=False)
    return build("drive", "v3", credentials=creds)


def list_recent_photos(max_results=20):
    """Lista elementos recientes de Google Photos."""
    page_size = max(1, min(int(max_results or 20), 100))

    def _request_with_creds(creds_obj):
        headers = {'Authorization': f'Bearer {creds_obj.token}'}
        url = "https://photoslibrary.googleapis.com/v1/mediaItems"
        return requests.get(url, headers=headers, params={"pageSize": page_size}, timeout=30)

    try:
        creds = get_google_credentials(require_photos=True, allow_interactive=False)
    except Exception as e:
        logger.warning("Google Photos no disponible: %s", e)
        return []

    resp = _request_with_creds(creds)

    if resp.status_code == 403:
        try:
            payload = resp.json() if resp.content else {}
        except Exception:
            payload = {}
        err = (payload or {}).get("error") or {}
        msg = str(err.get("message") or "")
        if "insufficient authentication scopes" in msg.lower():
            try:
                alt_creds = get_google_credentials(
                    require_photos=True,
                    require_drive_write=True,
                    allow_interactive=False,
                )
                resp = _request_with_creds(alt_creds)
            except Exception as alt_exc:
                logger.warning("Google Photos reintento con token manage_full falló: %s", alt_exc)

    if resp.status_code >= 400:
        detail = ""
        action_hint = (
            "Acción: ejecutar POST /agente/photos/authorize con include_drive_write=true, "
            "habilitar Photos Library API y agregar tu cuenta en OAuth Test Users."
        )
        try:
            payload = resp.json()
            err = (payload or {}).get("error") or {}
            msg = err.get("message") or ""
            status = err.get("status") or ""
            code = err.get("code") or resp.status_code
            detail = f"code={code} status={status} message={msg}".strip()
        except Exception:
            detail = resp.text[:500]
        raise RuntimeError(
            "Google Photos request failed. "
            f"HTTP {resp.status_code}. {detail}. {action_hint}"
        )
    items = resp.json().get("mediaItems", [])
    normalizados = []
    for p in items:
        normalizados.append({
            "id": p.get("id"),
            "filename": p.get("filename", "photo.jpg"),
            "mimeType": p.get("mimeType", ""),
            "baseUrl": p.get("baseUrl", ""),
            "productUrl": p.get("productUrl", ""),
            "mediaMetadata": p.get("mediaMetadata", {}),
        })
    return normalizados


def download_photo(photo_item: dict, destination: str) -> None:
    """Descarga una foto desde Google Photos usando baseUrl."""
    base_url = photo_item.get("baseUrl", "")
    if not base_url:
        raise ValueError("photo_item no tiene baseUrl")
    download_url = f"{base_url}=d"
    resp = requests.get(download_url, timeout=60)
    resp.raise_for_status()
    with open(destination, "wb") as fh:
        fh.write(resp.content)


def download_photo_bytes(photo_item: dict) -> bytes:
    """Descarga bytes de una foto desde Google Photos usando baseUrl."""
    base_url = photo_item.get("baseUrl", "")
    if not base_url:
        raise ValueError("photo_item no tiene baseUrl")
    download_url = f"{base_url}=d"
    resp = requests.get(download_url, timeout=60)
    resp.raise_for_status()
    return resp.content


def authorize_drive():
    """Helper para forzar flujo OAuth y guardar token."""
    # simplemente intenta obtener el servicio, lo que disparará el flujo
    creds = get_google_credentials(require_photos=False, require_drive_write=True, allow_interactive=True)
    svc = build("drive", "v3", credentials=creds)
    # dump info breve
    try:
        info = svc.about().get(fields="user").execute()
        logger.info("Credenciales de Google autorizadas para: %s", info.get('user', {}).get('emailAddress'))
    except Exception as exc:
        logger.debug("No fue posible obtener información de usuario de Drive: %s", exc)
    return svc


def authorize_drive_interactive(require_write: bool = True) -> Dict:
    """Run interactive OAuth flow to bootstrap Drive token."""
    creds = get_google_credentials(
        require_photos=False,
        require_drive_write=require_write,
        allow_interactive=True,
    )
    token_file = AUTH_DIR / ("token_google_manage.json" if require_write else "token_google_drive.json")
    return {
        "ok": bool(creds and creds.valid),
        "require_write": require_write,
        "token_file": str(token_file),
        "credentials_file": str(_resolve_google_credentials_file(require_drive_write=require_write)),
    }


def authorize_photos_interactive(include_drive_write: bool = False) -> Dict:
    """Run interactive OAuth flow to bootstrap Google Photos token.

    include_drive_write=True genera token combinado Drive(write)+Photos para pipelines unificados.
    """
    creds = get_google_credentials(
        require_photos=True,
        require_drive_write=include_drive_write,
        allow_interactive=True,
    )
    if include_drive_write:
        token_file = AUTH_DIR / "token_google_manage_full.json"
    else:
        token_file = AUTH_DIR / "token_google_full.json"

    return {
        "ok": bool(creds and creds.valid),
        "include_drive_write": include_drive_write,
        "token_file": str(token_file),
        "credentials_file": str(_resolve_google_credentials_file(require_drive_write=include_drive_write)),
    }


def list_recent_files(max_results=10):
    """List recent files in Google Drive in JSON-serializable format."""
    service = get_drive_service()
    results = service.files().list(
        pageSize=max_results,
        fields="files(id, name, mimeType, modifiedTime, size)",
        orderBy="modifiedTime desc"
    ).execute()
    return results.get("files", [])


def list_recent_files_detailed(max_results=50):
    """List recent files with parents/appProperties for classification workflows."""
    service = get_drive_manage_service()
    results = service.files().list(
        pageSize=max_results,
        fields="files(id, name, mimeType, modifiedTime, size, parents, appProperties)",
        orderBy="modifiedTime desc"
    ).execute()
    return results.get("files", [])


def list_unclassified_drive_files_detailed(max_results=50, include_trashed: bool = False, full_scan: bool = False):
    """List Drive files pendientes de clasificación por NEXO.

    - include_trashed=True incluye archivos en papelera.
    - full_scan=True pagina hasta agotar resultados (en lugar de una sola página).
    """
    service = get_drive_manage_service()
    max_results = max(1, min(int(max_results), 10000))
    page_size = min(max_results, 1000)

    query_parts = [
        "mimeType!='application/vnd.google-apps.folder'",
        "not appProperties has { key='nexo_source' and value='google_drive' }",
    ]
    if not include_trashed:
        query_parts.insert(0, "trashed=false")

    query = " and ".join(query_parts)
    items = []
    page_token = None

    while True:
        results = service.files().list(
            q=query,
            pageSize=page_size,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, size, parents, appProperties, trashed)",
            orderBy="modifiedTime desc",
            pageToken=page_token,
        ).execute()

        page_items = results.get("files", [])
        items.extend(page_items)

        if not full_scan:
            break
        if len(items) >= max_results:
            break

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    return items[:max_results]


def list_files_in_folder(folder_id: str, max_results: int = 50):
    """List files inside a specific Drive folder."""
    service = get_drive_manage_service()
    max_results = max(1, min(int(max_results), 1000))
    query = f"'{_escape_query_value(folder_id)}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        pageSize=max_results,
        fields="files(id, name, mimeType, modifiedTime, size, parents, appProperties)",
        orderBy="modifiedTime desc",
    ).execute()
    return results.get("files", [])


def download_drive_file(file_id: str, destination: str) -> None:
    """Download a file from Drive to the given local destination path."""
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    with open(destination, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()


def _escape_query_value(value: str) -> str:
    return value.replace("'", "\\'")


def ensure_drive_folder_path(path_parts, parent_id: str = "root") -> str:
    """Create/get nested folders in Drive and return the final folder id."""
    service = get_drive_manage_service()
    current_parent = parent_id
    for folder_name in path_parts:
        safe_name = _escape_query_value(folder_name)
        query = (
            f"mimeType='application/vnd.google-apps.folder' and "
            f"name='{safe_name}' and '{current_parent}' in parents and trashed=false"
        )
        found = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute().get("files", [])
        if found:
            current_parent = found[0]["id"]
            continue

        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [current_parent],
        }
        created = service.files().create(body=metadata, fields="id").execute()
        current_parent = created["id"]
    return current_parent


def find_drive_file_by_app_properties(app_properties: Dict[str, str], parent_id: Optional[str] = None):
    """Search a Drive file by appProperties key/value pairs."""
    service = get_drive_manage_service()
    conditions = ["trashed=false"]
    for key, value in app_properties.items():
        safe_key = _escape_query_value(str(key))
        safe_value = _escape_query_value(str(value))
        conditions.append(f"appProperties has {{ key='{safe_key}' and value='{safe_value}' }}")

    if parent_id:
        conditions.append(f"'{_escape_query_value(parent_id)}' in parents")

    query = " and ".join(conditions)
    found = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name, mimeType, parents, appProperties)",
        pageSize=1,
    ).execute().get("files", [])
    return found[0] if found else None


def upload_bytes_to_drive(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    parent_id: Optional[str] = None,
    app_properties: Optional[Dict[str, str]] = None,
):
    """Upload bytes into Drive with optional parent folder and appProperties."""
    service = get_drive_manage_service()
    metadata: Dict[str, Any] = {"name": filename}
    if parent_id:
        metadata["parents"] = [parent_id]
    if app_properties:
        metadata["appProperties"] = {str(k): str(v) for k, v in app_properties.items()}

    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type or "application/octet-stream", resumable=True)
    return service.files().create(
        body=metadata,
        media_body=media,
        fields="id, name, mimeType, parents, appProperties",
    ).execute()


def upload_local_file_to_drive(file_path: str, parent_id: Optional[str] = None, name: Optional[str] = None, app_properties: Optional[Dict[str, str]] = None):
    """Upload local file path to Drive folder."""
    file_path_obj = Path(file_path)
    payload = file_path_obj.read_bytes()
    guessed_mime, _ = mimetypes.guess_type(str(file_path_obj))
    return upload_bytes_to_drive(
        file_bytes=payload,
        filename=name or file_path_obj.name,
        mime_type=guessed_mime or "application/octet-stream",
        parent_id=parent_id,
        app_properties=app_properties,
    )


def move_drive_file_to_folder(file_id: str, target_parent_id: str, app_properties: Optional[Dict[str, str]] = None):
    """Move an existing Drive file to target folder, optionally patch appProperties."""
    service = get_drive_manage_service()
    file_info = service.files().get(fileId=file_id, fields="id, parents, appProperties").execute()
    existing_parents = file_info.get("parents", [])
    remove_parents = ",".join(existing_parents) if existing_parents else None

    body = None
    if app_properties:
        merged = dict(file_info.get("appProperties") or {})
        merged.update({str(k): str(v) for k, v in app_properties.items()})
        body = {"appProperties": merged}

    return service.files().update(
        fileId=file_id,
        addParents=target_parent_id,
        removeParents=remove_parents,
        body=body,
        fields="id, name, parents, appProperties",
    ).execute()


def rename_drive_file(file_id: str, new_name: str):
    """Rename a Drive file."""
    service = get_drive_manage_service()
    return service.files().update(
        fileId=file_id,
        body={"name": new_name},
        fields="id, name, parents",
    ).execute()


def trash_drive_file(file_id: str, trashed: bool = True):
    """Move a Drive file to/from trash."""
    service = get_drive_manage_service()
    return service.files().update(
        fileId=file_id,
        body={"trashed": bool(trashed)},
        fields="id, name, trashed",
    ).execute()


def delete_drive_file(file_id: str) -> Dict[str, bool]:
    """Permanently delete a Drive file."""
    service = get_drive_manage_service()
    service.files().delete(fileId=file_id).execute()
    return {"deleted": True}


# small compatibility wrapper class so existing code does not break
class GoogleConnector:
    def list_drive_files(self, page_size: int = 10):
        return list_recent_files(page_size)

    def list_files_in_folder(self, folder_id: str, page_size: int = 50):
        return list_files_in_folder(folder_id, page_size)

    def list_drive_files_detailed(self, page_size: int = 50):
        return list_recent_files_detailed(page_size)

    def list_unclassified_drive_files_detailed(self, page_size: int = 50, include_trashed: bool = False, full_scan: bool = False):
        return list_unclassified_drive_files_detailed(page_size, include_trashed=include_trashed, full_scan=full_scan)

    def download_drive_file(self, file_id: str, destination: str):
        return download_drive_file(file_id, destination)

    def upload_local_file(self, file_path: str, parent_id: Optional[str] = None, name: Optional[str] = None, app_properties: Optional[Dict[str, str]] = None):
        return upload_local_file_to_drive(file_path, parent_id=parent_id, name=name, app_properties=app_properties)

    def list_photos(self, page_size: int = 20):
        return list_recent_photos(page_size)

    def download_photo(self, photo_item: dict, destination: str):
        return download_photo(photo_item, destination)

    def download_photo_bytes(self, photo_item: dict) -> bytes:
        return download_photo_bytes(photo_item)

    def ensure_folder_path(self, path_parts, parent_id: str = "root") -> str:
        return ensure_drive_folder_path(path_parts, parent_id=parent_id)

    def find_file_by_app_properties(self, app_properties: Dict[str, str], parent_id: Optional[str] = None):
        return find_drive_file_by_app_properties(app_properties, parent_id=parent_id)

    def upload_bytes(self, file_bytes: bytes, filename: str, mime_type: str, parent_id: Optional[str] = None, app_properties: Optional[Dict[str, str]] = None):
        return upload_bytes_to_drive(file_bytes, filename, mime_type, parent_id=parent_id, app_properties=app_properties)

    def move_file_to_folder(self, file_id: str, target_parent_id: str, app_properties: Optional[Dict[str, str]] = None):
        return move_drive_file_to_folder(file_id, target_parent_id, app_properties=app_properties)

    def rename_file(self, file_id: str, new_name: str):
        return rename_drive_file(file_id, new_name)

    def trash_file(self, file_id: str, trashed: bool = True):
        return trash_drive_file(file_id, trashed=trashed)

    def delete_file(self, file_id: str):
        return delete_drive_file(file_id)


if __name__ == "__main__":
    files = list_recent_files()
    logger.info(json.dumps(files, indent=2))
