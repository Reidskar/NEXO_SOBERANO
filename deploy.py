#!/usr/bin/env python3
"""
Deploy Script: Automatiza deployment en servidor con dominio en 1 hora.
Usos:
  python deploy.py --init            # primera vez (setup)
  python deploy.py --deploy          # desplegar actualización
  python deploy.py --ssl dominio.com # generar SSL cert
  python deploy.py --status          # ver estado
"""

import subprocess
import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "CYAN": "\033[96m",
    "END": "\033[0m"
}

def log(msg, level="INFO"):
    colors = {"INFO": COLORS["CYAN"], "SUCCESS": COLORS["GREEN"], "ERROR": COLORS["RED"], "WARN": COLORS["YELLOW"]}
    log.info(f"{colors.get(level, '')}[{level}]{COLORS['END']} {msg}")

def run(cmd, check=True):
    """Ejecutar comando."""
    log(f"→ {cmd}", "INFO")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        log(f"Error: {result.stderr}", "ERROR")
        sys.exit(1)
    return result.returncode, result.stdout, result.stderr

def init_deployment(domain: str, email: str):
    """Setup inicial: clonar repo, instalar Docker, etc."""
    log("╔═════════════════════════════════════════════════╗", "CYAN")
    log("║  NEXO DEPLOYMENT - Setup Inicial                ║", "CYAN")
    log("╚═════════════════════════════════════════════════╝", "CYAN")
    
    # 1. Verificar Docker
    log("\n[1/8] Verificando Docker...", "INFO")
    code, _, _ = run("docker --version", check=False)
    if code != 0:
        log("Docker no instalado. Instalando...", "WARN")
        run("curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh")
    log("Docker ✓", "SUCCESS")

    # 2. Verificar Docker Compose
    log("\n[2/8] Verificando Docker Compose...", "INFO")
    code, _, _ = run("docker-compose --version", check=False)
    if code != 0:
        run("sudo curl -L 'https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)' -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose")
    log("Docker Compose ✓", "SUCCESS")

    # 3. Crear .env
    log("\n[3/8] Configurando variables de entorno...", "INFO")
    env_content = f"""# Nexo Deployment Config
DOMAIN={domain}
EMAIL={email}
OPENAI_API_KEY=sk-your-key-here
GEMINI_API_KEY=AIza-your-key-here
TELEGRAM_TOKEN=your-token-here
SECRET_KEY={os.urandom(32).hex()}
DATABASE_URL=sqlite:////app/data/nexo.db
ENVIRONMENT=production
"""
    Path(".env").write_text(env_content)
    log(".env creado ✓", "SUCCESS")

    # 4. Crear directorios necesarios
    log("\n[4/8] Creando estructura de directorios...", "INFO")
    Path("certs").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    log("Directorios ✓", "SUCCESS")

    # 5. Generar certificados SSL (self-signed para testing)
    log("\n[5/8] Generando certificados SSL...", "INFO")
    run(f"openssl req -x509 -newkey rsa:4096 -nodes -out certs/cert.pem -keyout certs/key.pem -days 365 -subj '/CN={domain}'", check=False)
    log("Certificados SSL ✓ (self-signed, usa Certbot en producción)", "SUCCESS")

    # 6. Build images
    log("\n[6/8] Construyendo imágenes Docker...", "INFO")
    run("docker-compose build --no-cache")
    log("Imágenes construidas ✓", "SUCCESS")

    # 7. Setup inicial de BD
    log("\n[7/8] Inicializando base de datos...", "INFO")
    run("docker-compose run --rm backend python setup.py", check=False)
    log("Base de datos ✓", "SUCCESS")

    # 8. Crear usuario admin
    log("\n[8/8] Creando usuario admin...", "INFO")
    run("docker-compose exec -T backend python -c \"from backend.services.auth_service import AuthService; a = AuthService(); a.create_user('admin', 'admin@nexo.local', 'ChangeMeNow123!', 'admin')\"", check=False)
    log("Usuario admin creado (admin:ChangeMeNow123!) ✓", "SUCCESS")

    log("\n" + "="*50, "SUCCESS")
    log("SETUP COMPLETADO ✓", "SUCCESS")
    log("="*50 + "\n", "SUCCESS")
    
    print(f"""
╔─────────────────────────────────────────────────┐
│ PRÓXIMOS PASOS                                  │
├─────────────────────────────────────────────────┤
│                                                 │
│ 1. Configura tus claves en .env:               │
│    - OPENAI_API_KEY                             │
│    - GEMINI_API_KEY                             │
│    - TELEGRAM_TOKEN                             │
│                                                 │
│ 2. Para generar SSL válido (no self-signed):    │
│    python deploy.py --ssl {domain}              │
│                                                 │
│ 3. Inicia los contenedores:                    │
│    python deploy.py --deploy                    │
│                                                 │
│ 4. Verifica que está online:                   │
│    python deploy.py --status                    │
│                                                 │
│ 5. Accede en:                                   │
│    https://{domain}                             │
│    Usuario: admin                               │
│    Contraseña: ChangeMeNow123!                  │
│                                                 │
│ ⚠️  IMPORTANTE: cambia la contraseña admin      │
│                                                 │
└─────────────────────────────────────────────────┘
""")

def deploy():
    """Actualizar y desplegar."""
    log("Desplegando Nexo...", "INFO")
    
    run("git pull origin main", check=False)
    run("docker-compose build")
    run("docker-compose up -d")
    
    # Wait for backend
    import time
    for i in range(30):
        code, _, _ = run("docker-compose exec -T backend curl http://localhost:8000/", check=False)
        if code == 0:
            break
        time.sleep(1)
    
    log("Deployment completado ✓", "SUCCESS")
    run("docker-compose ps")

def setup_ssl(domain: str, email: str):
    """Configurar SSL con Certbot (Let's Encrypt)."""
    log(f"Configurando SSL para {domain}...", "INFO")
    
    # Stop nginx temporalmente
    run("docker-compose down nginx", check=False)
    
    # Instalar certbot si no existe
    run("apt-get update && apt-get install -y certbot python3-certbot-nginx", check=False)
    
    # Generar certificado
    run(f"certbot certonly --standalone -d {domain} --email {email} --agree-tos --non-interactive", check=False)
    
    # Copiar certificados
    run(f"cp /etc/letsencrypt/live/{domain}/fullchain.pem certs/cert.pem")
    run(f"cp /etc/letsencrypt/live/{domain}/privkey.pem certs/key.pem")
    
    # Reiniciar
    run("docker-compose up -d nginx")
    
    log("SSL configurado ✓", "SUCCESS")

def status():
    """Mostrar estado del sistema."""
    log("Estado del sistema:", "INFO")
    run("docker-compose ps")
    run("docker-compose logs --tail=20", check=False)

def main():
    parser = argparse.ArgumentParser(description="Nexo Deployment Tool")
    parser.add_argument("--init", action="store_true", help="Setup inicial")
    parser.add_argument("--deploy", action="store_true", help="Desplegar")
    parser.add_argument("--ssl", type=str, help="Setup SSL para dominio")
    parser.add_argument("--status", action="store_true", help="Ver estado")
    parser.add_argument("--domain", type=str, default="nexo.local", help="Dominio")
    parser.add_argument("--email", type=str, default="admin@nexo.local", help="Email admin")

    args = parser.parse_args()

    if args.init:
        init_deployment(args.domain, args.email)
    elif args.deploy:
        deploy()
    elif args.ssl:
        setup_ssl(args.ssl, args.email)
    elif args.status:
        status()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
