"""Runner del monitor X/Grok para ejecución puntual o en loop."""

from __future__ import annotations

import argparse
import json
import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.x_monitor import monitor_x_once, run_x_monitor_loop

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor X/Grok -> NEXO")
    parser.add_argument("--once", action="store_true", help="Ejecuta una sola vez")
    parser.add_argument("--limit", type=int, default=20, help="Máximo de tweets por consulta")
    parser.add_argument("--interval", type=int, default=900, help="Intervalo loop en segundos")
    parser.add_argument("--username", type=str, default=None, help="Usuario X a monitorear")
    args = parser.parse_args()

    if args.once:
        result = monitor_x_once(limit=args.limit, username=args.username)
        log.info(json.dumps(result, ensure_ascii=False, indent=2))
        return

    run_x_monitor_loop(interval_seconds=args.interval, limit=args.limit, username=args.username)


if __name__ == "__main__":
    main()
