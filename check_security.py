import requests
import os
from dotenv import load_dotenv

load_dotenv()

# CONFIGURACIÓN
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "Reidskar"
REPO_NAME = "NEXO_SOBERANO"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_security_alerts():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/code-scanning/alerts"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        alerts = response.json()
        open_alerts = [a for a in alerts if a['state'] == 'open']
        log.info(f"🔍 Alertas de Seguridad Abiertas: {len(open_alerts)}")
        for alert in open_alerts:
            log.info(f"⚠️ [{alert['rule']['severity']}] {alert['rule']['description']}")
    else:
        log.info(f"❌ Error al consultar GitHub: {response.status_code}")

if __name__ == "__main__":
    get_security_alerts()
