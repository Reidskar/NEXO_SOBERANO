"""
NEXO SOBERANO — Tools Registry
Herramientas integradas y reescritas para el stack NEXO.
© 2026 elanarcocapital.com
"""
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
TOOLS_AVAILABLE = [
    d.name for d in TOOLS_DIR.iterdir()
    if d.is_dir() and not d.name.startswith('_')
]

__all__ = ["TOOLS_AVAILABLE", "TOOLS_DIR"]
