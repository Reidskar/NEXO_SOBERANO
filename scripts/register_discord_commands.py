"""scripts/register_discord_commands.py — Registra slash commands en Discord via REST."""
from __future__ import annotations
import os, sys, json, urllib.request, urllib.error
from pathlib import Path

def _load_env():
    for p in [Path(__file__).parents[1]/".env", Path(".env")]:
        if p.exists():
            for line in p.read_text().splitlines():
                line=line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k,_,v=line.partition("=")
                    if k.strip() not in os.environ:
                        os.environ[k.strip()]=v.strip().strip('"').strip("'")
            break

_load_env()
TOKEN     = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN","")
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID","")
GUILD_ID  = os.getenv("DISCORD_GUILD_ID","")
API       = "https://discord.com/api/v10"

COMMANDS=[
  {"name":"nexo","description":"Pregunta a NEXO (Gemma 4 → Gemini fallback)","options":[{"name":"query","description":"Tu pregunta","type":3,"required":True}]},
  {"name":"ai","description":"Inteligencia principal con contexto persistente","options":[{"name":"pregunta","description":"Tu pregunta","type":3,"required":True},{"name":"recordar","description":"Mantener contexto","type":5,"required":False}]},
  {"name":"memoria","description":"Gestiona contexto con NEXO","options":[{"name":"accion","description":"ver o limpiar","type":3,"required":False,"choices":[{"name":"Ver contexto","value":"ver"},{"name":"Limpiar contexto","value":"limpiar"}]}]},
  {"name":"status","description":"Métricas del sistema NEXO","options":[]},
  {"name":"unirse","description":"NEXO se une a tu canal de voz","options":[]},
  {"name":"salir","description":"NEXO abandona el canal de voz","options":[]},
  {"name":"drive","description":"Busca en el Drive NEXO","options":[{"name":"consulta","description":"Qué buscar","type":3,"required":True}]},
  {"name":"geopolitica","description":"Consulta carpeta Geopolítica","options":[{"name":"tema","description":"Tema","type":3,"required":False}]},
  {"name":"phone","description":"Control remoto del teléfono","options":[
    {"name":"accion","description":"Acción","type":3,"required":True,
     "choices":[
       {"name":"Silenciar","value":"silence"},{"name":"Restaurar volumen","value":"unsilence"},
       {"name":"Encontrar teléfono","value":"find"},{"name":"GPS","value":"locate"},
       {"name":"Foto","value":"camera"},{"name":"Captura","value":"screenshot"},
       {"name":"Bloquear","value":"lock_screen"},{"name":"Linterna ON","value":"torch_on"},
       {"name":"Linterna OFF","value":"torch_off"},{"name":"Wake-up","value":"wakeup"},
       {"name":"Ping","value":"ping"}
     ]},
    {"name":"dispositivo","description":"ID dispositivo","type":3,"required":False},
    {"name":"mensaje","description":"Mensaje","type":3,"required":False}
  ]},
]

def register_commands():
    if not TOKEN:  return {"ok":False,"error":"DISCORD_BOT_TOKEN no configurado"}
    if not CLIENT_ID: return {"ok":False,"error":"DISCORD_CLIENT_ID no configurado"}
    path = f"/applications/{CLIENT_ID}/guilds/{GUILD_ID}/commands" if GUILD_ID else f"/applications/{CLIENT_ID}/commands"
    scope = f"guild {GUILD_ID} (instantáneo)" if GUILD_ID else "global (hasta 1h)"
    req=urllib.request.Request(f"{API}{path}",data=json.dumps(COMMANDS).encode(),method="PUT",
        headers={"Authorization":f"Bot {TOKEN}","Content-Type":"application/json","User-Agent":"NEXO/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=15) as r:
            return {"ok":True,"status":r.status,"scope":scope,"commands":[c["name"] for c in COMMANDS],"count":len(COMMANDS)}
    except urllib.error.HTTPError as e:
        return {"ok":False,"status":e.code,"error":e.read().decode(errors="replace"),"scope":scope}

if __name__=="__main__":
    print("Registrando slash commands NEXO...")
    r=register_commands()
    if r.get("ok"):
        print(f"✓ {r['count']} comandos registrados ({r['scope']})")
        print(f"  {', '.join(r['commands'])}")
    else:
        print(f"✗ Error {r.get('status')}: {r.get('error')}")
        sys.exit(1)
