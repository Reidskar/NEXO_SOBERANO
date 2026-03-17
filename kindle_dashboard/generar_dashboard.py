"""
Genera imagen PNG con métricas NEXO para mostrar en Kindle Paperwhite.
Se copia directamente a E:\documents\ sin jailbreak.
Resolución Kindle PW 1ª gen: 758x1024 px, escala de grises.
"""
import requests
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

BACKEND = os.getenv("NEXO_BACKEND", "http://localhost:8000")
OUTPUT_PATH = os.getenv("KINDLE_PATH", "E:\\documents\\nexo_status.png")
WIDTH, HEIGHT = 758, 1024

def obtener_metricas() -> dict:
    try:
        r = requests.get(f"{BACKEND}/api/metrics/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def obtener_agentes() -> dict:
    try:
        r = requests.get(f"{BACKEND}/api/mobile/agents", timeout=5)
        return r.json().get("agentes", {})
    except:
        return {}

def generar_imagen(metricas: dict, agentes: dict) -> Image:
    img = Image.new("L", (WIDTH, HEIGHT), color=255)  # L = grayscale
    draw = ImageDraw.Draw(img)

    # Intentar fuente monospace, fallback a default
    try:
        font_title = ImageFont.truetype("cour.ttf", 36)
        font_body  = ImageFont.truetype("cour.ttf", 28)
        font_small = ImageFont.truetype("cour.ttf", 22)
    except:
        font_title = ImageFont.load_default()
        font_body  = font_title
        font_small = font_title

    y = 40
    # Título
    draw.text((40, y), "NEXO SOBERANO", font=font_title, fill=0)
    y += 50
    draw.line([(40, y), (WIDTH-40, y)], fill=0, width=2)
    y += 20

    # Timestamp
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    draw.text((40, y), f"Actualizado: {now}", font=font_small, fill=80)
    y += 50

    # Métricas del PC
    draw.text((40, y), "[ NODO PC ]", font=font_body, fill=0)
    y += 40

    if "error" not in metricas:
        sys = metricas.get("system", metricas.get("sistema", {}))
        cpu = sys.get("cpu_percent", sys.get("uso_pct", "?"))
        ram = sys.get("memory_percent", sys.get("uso_pct", "?"))
        uptime = metricas.get("uptime_legible", metricas.get("uptime_segundos", "?"))
        version = metricas.get("version", "?")

        draw.text((60, y), f"CPU:    {cpu}%", font=font_body, fill=0); y += 40
        draw.text((60, y), f"RAM:    {ram}%", font=font_body, fill=0); y += 40
        draw.text((60, y), f"Uptime: {uptime}", font=font_body, fill=0); y += 40
        draw.text((60, y), f"Ver:    {version}", font=font_body, fill=0); y += 50
    else:
        draw.text((60, y), f"Error: {metricas['error'][:40]}", font=font_small, fill=80)
        y += 50

    # Agentes móviles
    draw.line([(40, y), (WIDTH-40, y)], fill=0, width=1); y += 20
    draw.text((40, y), "[ NODO MOVIL ]", font=font_body, fill=0); y += 40

    if agentes:
        for agent_id, data in agentes.items():
            draw.text((60, y), f"{agent_id}", font=font_small, fill=0); y += 30
            cpu_m = data.get("cpu_pct", "?")
            ram_m = data.get("ram_pct", "?")
            bat   = data.get("bateria_pct", "?")
            contacto = data.get("ultimo_contacto", "?")[:16]
            draw.text((60, y), f"CPU:{cpu_m}% RAM:{ram_m}% BAT:{bat}%", font=font_small, fill=0); y += 30
            draw.text((60, y), f"Ultimo: {contacto}", font=font_small, fill=80); y += 40
    else:
        draw.text((60, y), "Sin agentes conectados", font=font_small, fill=120); y += 40

    # Footer
    draw.line([(40, HEIGHT-60), (WIDTH-40, HEIGHT-60)], fill=0, width=1)
    draw.text((40, HEIGHT-45), "github.com/Reidskar/NEXO_SOBERANO", font=font_small, fill=120)

    return img

def main():
    log.info("[KINDLE] Obteniendo métricas...")
    metricas = obtener_metricas()
    agentes  = obtener_agentes()
    
    log.info("[KINDLE] Generando imagen...")
    img = generar_imagen(metricas, agentes)
    
    log.info(f"[KINDLE] Guardando en {OUTPUT_PATH}...")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    img.save(OUTPUT_PATH, "PNG")
    log.info(f"[KINDLE] OK — {WIDTH}x{HEIGHT}px guardado")

if __name__ == "__main__":
    main()
