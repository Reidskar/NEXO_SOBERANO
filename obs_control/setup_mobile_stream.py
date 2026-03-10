from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "obs_control" / "mobile_profiles.generated.json"


def build_profiles(server: str, stream_key: str) -> dict:
    endpoint = f"{server.rstrip('/')}/{stream_key}"
    return {
        "meta": {
            "generated_by": "NEXO mobile setup",
            "output": str(OUTPUT),
            "stream_endpoint": endpoint,
        },
        "profiles": {
            "phone_720p30_stable": {
                "app": "Larix/PRISM/Streamlabs",
                "video": {
                    "resolution": "1280x720",
                    "fps": 30,
                    "bitrate_kbps": 3000,
                    "keyframe_interval": 2,
                },
                "audio": {
                    "bitrate_kbps": 128,
                    "sample_rate": 44100,
                },
                "transport": {
                    "protocol": "RTMP",
                    "url": server,
                    "stream_key": stream_key,
                    "full_endpoint": endpoint,
                    "reconnect": True,
                    "retries": 25,
                },
            },
            "tablet_1080p30_balanced": {
                "app": "Larix/PRISM",
                "video": {
                    "resolution": "1920x1080",
                    "fps": 30,
                    "bitrate_kbps": 4500,
                    "keyframe_interval": 2,
                },
                "audio": {
                    "bitrate_kbps": 160,
                    "sample_rate": 48000,
                },
                "transport": {
                    "protocol": "RTMP",
                    "url": server,
                    "stream_key": stream_key,
                    "full_endpoint": endpoint,
                    "reconnect": True,
                    "retries": 20,
                },
            },
            "phone_low_bandwidth_540p": {
                "app": "Larix/PRISM/Streamlabs",
                "video": {
                    "resolution": "960x540",
                    "fps": 30,
                    "bitrate_kbps": 1800,
                    "keyframe_interval": 2,
                },
                "audio": {
                    "bitrate_kbps": 96,
                    "sample_rate": 44100,
                },
                "transport": {
                    "protocol": "RTMP",
                    "url": server,
                    "stream_key": stream_key,
                    "full_endpoint": endpoint,
                    "reconnect": True,
                    "retries": 30,
                },
            },
        },
        "operational_notes": [
            "No transmitir al mismo tiempo desde PC y móvil/tablet con la misma stream key.",
            "Usar la misma URL + stream key en todos los dispositivos para failover rápido.",
            "Si el móvil calienta, bajar a perfil 540p.",
            "Activar modo No Molestar y bloquear orientación en el teléfono.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera perfiles de streaming para teléfono/tablet")
    parser.add_argument("--server", default="rtmp://your-server/live", help="RTMP server base URL")
    parser.add_argument("--key", default="your-stream-key", help="Stream key")
    args = parser.parse_args()

    data = build_profiles(args.server, args.key)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("✅ Perfiles móviles generados")
    log.info(f"📄 Archivo: {OUTPUT}")
    log.info(f"🎯 Endpoint RTMP: {data['meta']['stream_endpoint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
