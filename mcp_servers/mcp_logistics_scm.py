"""
MCP Server: SCM Logistics Optimizer
Corre localmente via stdio. Sin dependencias externas.
"""
import asyncio
import json
import sys
from typing import Any

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    from pulp import LpProblem, LpMinimize, LpVariable, lpSum, value
    HAS_PULP = True
except ImportError:
    HAS_PULP = False


def optimize_routes(nodes: list, distances: dict) -> dict:
    """Optimiza rutas logísticas usando NetworkX."""
    if not HAS_NETWORKX:
        return {"error": "networkx no instalado. Ejecutar: pip install networkx"}
    
    G = nx.Graph()
    for node in nodes:
        G.add_node(node)
    for (src, dst), dist in distances.items():
        G.add_edge(src, dst, weight=dist)
    
    results = {}
    for src in nodes:
        for dst in nodes:
            if src != dst:
                try:
                    path = nx.shortest_path(G, src, dst, weight='weight')
                    cost = nx.shortest_path_length(G, src, dst, weight='weight')
                    results[f"{src}->{dst}"] = {"path": path, "cost": cost}
                except nx.NetworkXNoPath:
                    results[f"{src}->{dst}"] = {"error": "sin ruta"}
    
    return {"routes": results, "nodes": len(nodes)}


def calculate_kpis(inventory: dict) -> dict:
    """Calcula KPIs básicos de inventario."""
    total_items = sum(inventory.values())
    avg_stock = total_items / len(inventory) if inventory else 0
    low_stock = {k: v for k, v in inventory.items() if v < avg_stock * 0.2}
    
    return {
        "total_items": total_items,
        "avg_stock": round(avg_stock, 2),
        "low_stock_alerts": low_stock,
        "coverage_ratio": round((len(inventory) - len(low_stock)) / len(inventory), 2) if inventory else 0
    }


def handle_request(request: dict) -> dict:
    """Router principal de herramientas MCP."""
    tool = request.get("tool")
    params = request.get("params", {})
    
    if tool == "optimize_routes":
        return optimize_routes(params.get("nodes", []), params.get("distances", {}))
    elif tool == "calculate_kpis":
        return calculate_kpis(params.get("inventory", {}))
    elif tool == "health":
        return {
            "status": "ok",
            "networkx": HAS_NETWORKX,
            "pulp": HAS_PULP,
            "server": "mcp_logistics_scm v1.0"
        }
    else:
        return {"error": f"Herramienta desconocida: {tool}"}


if __name__ == "__main__":
    # Modo stdio para MCP local
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            print(json.dumps({"error": "JSON inválido"}), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)
