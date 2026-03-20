"""
NEXO SOBERANO — Tools Registry
Herramientas integradas y reescritas para el stack NEXO.
© 2026 elanarcocapital.com
"""
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
TOOLS_AVAILABLE = [
    "circuit_breaker",
    "inter_agent_bus",
    "mcp_logistics_scm"
]

__all__ = ["TOOLS_AVAILABLE", "TOOLS_DIR"]
