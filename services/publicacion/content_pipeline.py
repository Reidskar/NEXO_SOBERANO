"""Pipeline de publicación para contenido público de geopolítica."""

import json
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
WEB_API_DIR = ROOT_DIR / "NEXO_SOBERANO" / "web_api"
PUBLIC_FILE = WEB_API_DIR / "geopolitica_publica.json"


def _load_public_feed() -> dict:
	WEB_API_DIR.mkdir(parents=True, exist_ok=True)
	if not PUBLIC_FILE.exists():
		return {"updated_at": None, "items": []}
	try:
		return json.loads(PUBLIC_FILE.read_text(encoding="utf-8"))
	except Exception:
		return {"updated_at": None, "items": []}


def _save_public_feed(data: dict) -> None:
	data["updated_at"] = datetime.now().isoformat()
	PUBLIC_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def publicar_drive_geopolitica(item: dict) -> None:
	"""
	Publica un item proveniente de Google Drive al feed público geopolítico.
	"""
	data = _load_public_feed()
	items = data.get("items", [])

	item_id = item.get("id") or item.get("hash") or item.get("nombre")
	if not item_id:
		return

	normalized = {
		"id": item_id,
		"origen": "GoogleDrive",
		"categoria": "GEOPOLITICA_PUBLICA",
		"publico": True,
		"nombre": item.get("nombre", ""),
		"resumen": item.get("resumen", ""),
		"impacto": item.get("impacto", "Medio"),
		"fecha": datetime.now().isoformat(),
		"link": item.get("link", ""),
	}

	replaced = False
	for idx, existing in enumerate(items):
		if existing.get("id") == item_id:
			items[idx] = normalized
			replaced = True
			break
	if not replaced:
		items.append(normalized)

	data["items"] = items[-500:]
	_save_public_feed(data)
