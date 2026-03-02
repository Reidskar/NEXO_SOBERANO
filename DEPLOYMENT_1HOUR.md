# 🚀 GUÍA: ONLINE CON DOMINIO EN 1 HORA

Tu sistema Nexo completamente desplegado, online, con dominio real, SSL y autenticación.

---

## ⏱️ TIMELINE - 60 MINUTOS

| Tiempo | Tarea | Duración |
|--------|-------|----------|
| 0:00-0:10 | Preparar servidor + clonar repo | 10 min |
| 0:10-0:15 | Configurar variables .env | 5 min |
| 0:15-0:25 | Ejecutar setup de Docker | 10 min |
| 0:25-0:35 | Generar certificados SSL | 10 min |
| 0:35-0:50 | Deploy inicial | 15 min |
| 0:50-1:00 | Testing + ajustes finales | 10 min |

---

## 📋 PRE-REQUISITOS

### Tener listos:
1. **Servidor** (VPS/Cloud):
   - Ubuntu 20.04+ o similar
   - 2+ vCPU, 4GB RAM
   - SSH acceso root
   - Puertos 80, 443 abiertos

2. **Dominio**:
   - DNS apuntando a IP del servidor
   - Acceso a gestionar DNS (para Certbot)

3. **Credenciales API**:
   - `OPENAI_API_KEY` (Copilot)
   - `GEMINI_API_KEY` (Gemini)
   - `TELEGRAM_TOKEN` (opcional)

---

## 🔧 PASO 1: PREPARAR SERVIDOR (10 min)

SSH al servidor:
```bash
ssh root@tu-servidor-ip
```

Actualizar sistema:
```bash
apt-get update
apt-get upgrade -y
apt-get install -y git curl wget
```

Clonar repositorio (reemplaza con tu repo):
```bash
git clone https://github.com/tu-usuario/nexo-soberano.git
cd nexo-soberano
```

---

## 📝 PASO 2: CONFIGURAR .ENV (5 min)

Copiar template:
```bash
cp .env.example .env
```

Editar `.env` con tus credenciales:
```bash
nano .env
```

**Llenar estos campos obligatorios:**
```ini
DOMAIN=tu-dominio.com
EMAIL=admin@tu-dominio.com
OPENAI_API_KEY=sk-your-key-here
GEMINI_API_KEY=AIza-your-key-here
TELEGRAM_TOKEN=tu-token-aqui
SECRET_KEY=random-secret-key-here
```

**Para generar SECRET_KEY automáticamente:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🐳 PASO 3: SETUP DOCKER (10 min)

Instalar Docker (auto):
```bash
python3 deploy.py --init --domain tu-dominio.com --email admin@tu-dominio.com
```

Esto hará:
- ✓ Instalar Docker + Docker Compose
- ✓ Crear estructura de directorios
- ✓ Generar certificados SSL (self-signed)
- ✓ Construir imágenes
- ✓ Inicializar BD
- ✓ Crear usuario admin

**Output esperado:**
```
[INFO] Verificando Python...
[SUCCESS] Python 3.11 ✓
[INFO] Construyendo imágenes Docker...
[SUCCESS] Imágenes construidas ✓
...
[SUCCESS] SETUP COMPLETADO ✓
```

---

## 🔐 PASO 4: CERTIFICADO SSL VÁLIDO (10 min)

Una vez que el dominio apunta al servidor y todo está levantado:

```bash
python3 deploy.py --ssl tu-dominio.com --email admin@tu-dominio.com
```

Esto:
- ✓ Genera certificado Let's Encrypt válido
- ✓ Configura auto-renovación (90 días)
- ✓ Reinicia Nginx con SSL

---

## 🚀 PASO 5: DESPLEGAR (15 min)

Iniciar toda la infraestructura:
```bash
python3 deploy.py --deploy
```

Esto:
- ✓ Construye imágenes
- ✓ Inicia contenedores
- ✓ Expone en puertos 80/443
- ✓ Configura Nginx reverso proxy

**Verificar que está online:**
```bash
python3 deploy.py --status
```

Expected:
```
CONTAINER ID   STATUS      PORTS
xxxxx          Up 2 min    0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

---

## ✅ PASO 6: TESTING (10 min)

### Acceso al admin:

```
https://tu-dominio.com/admin_dashboard.html
```

**Credenciales:**
- Usuario: `admin`
- Contraseña: `ChangeMeNow123!`

**⚠️ CAMBIA LA CONTRASEÑA INMEDIATAMENTE**

### Cambiar contraseña admin:

```bash
docker-compose exec backend python3 -c "
from backend.services.auth_service import AuthService
a = AuthService()
a.deactivate_user(1)  # desactivar vieja
a.create_user('admin', 'admin@tu-dominio.com', 'TuNuevaContraseña123!', 'admin')
"
```

### Verificar Chat:

```
https://tu-dominio.com/chat.html
```

### Verificar APIs:

```bash
# Health check
curl https://tu-dominio.com/

# Login test
curl -X POST https://tu-dominio.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"TuNuevaContraseña123!"}'
```

---

## 📊 VERIFICACIONES FINALES

```bash
# Ver logs en vivo
docker-compose logs -f

# Verificar contenedores
docker-compose ps

# CPU/Memoria
docker stats
```

---

## 🔗 URLs DESPUÉS DE DESPLEGADO

- **Admin**: `https://tu-dominio.com/admin_dashboard.html`
- **Chat**: `https://tu-dominio.com/chat.html`
- **API Docs**: `https://tu-dominio.com/docs`
- **API Redoc**: `https://tu-dominio.com/redoc`

---

## 🛠️ TROUBLESHOOTING

### "Connection refused"
```bash
# Verificar que contenedores están levantados
docker-compose ps

# Reinicar
docker-compose restart
```

### "SSL certificate error"
```bash
# Regenerar SSL
python3 deploy.py --ssl tu-dominio.com --email admin@tu-dominio.com
```

### "API no responde"
```bash
# Ver logs del backend
docker-compose logs backend | tail -50

# Reiniciar backend
docker-compose restart backend
```

### "Puertos bloqueados"
```bash
# Ver qué usa los puertos
sudo lsof -i :80
sudo lsof -i :443

# Matar procesos si es necesario
sudo kill -9 <PID>
```

### "Sin almacenamiento"
```bash
# Ampliar volumen Docker
docker system df
docker system prune -a  # libera espacio

# O ampliar partición del servidor
df -h
```

---

## 📈 POST-DEPLOYMENT

### 1. Copia de seguridad automática

```bash
# Crear script backup diario
cat > /root/backup.sh << 'EOF'
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T backend sqlite3 /app/data/nexo.db ".dump" > /backup/nexo_$TIMESTAMP.sql
tar -czf /backup/logs_$TIMESTAMP.tar.gz /path/to/logs
echo "Backup $TIMESTAMP completado"
EOF

chmod +x /root/backup.sh

# Añadir a crontab (diario a las 3AM)
echo "0 3 * * * /root/backup.sh" | crontab -
```

### 2. Monitoreo

```bash
# Ver CPU/Memoria en tiempo real
docker stats

# Setup alertas (Uptimerobot.com)
# Monitorea https://tu-dominio.com/health cada 5 min
```

### 3. Autenticación a través de Discord (opcional)

En futuras versiones, integración OAuth con Discord para SSO.

---

## 🎯 RESUMEN - LO QUE TIENES

✅ Backend FastAPI completamente funcional

✅ IA dual (Copilot + Gemini) integrada

✅ Chat omnicanal (Telegram, WhatsApp, Facebook, Instagram)

✅ Autenticación JWT + Admin Panel

✅ SSL/HTTPS válido

✅ Nginx reverso proxy con rate limiting

✅ Docker containerizado para fácil scaling

✅ Base de datos SQLite (upgradeable a PostgreSQL)

✅ Historial conversacional persistente

✅ Diario unificado de todos los canales

---

## 📚 DOCUMENTACIÓN RELACIONADA

- `OPERATION_GUIDE.md` - Operación de sistemas
- `README_CHAT.md` - Sistema de chat
- `docker-compose.yml` - Orquestación containers
- `deploy.py` - Script deployment
- `admin_dashboard.html` - Panel de control

---

## 🎓 SIGUIENTES PASOS

Después de 1 hora online:

1. **Configurar webhooks** de redes sociales
2. **Integrar base de datos** PostgreSQL para producción
3. **Añadir CDN** (Cloudflare) para caché global
4. **Configurar backups** automáticos a AWS S3
5. **Añadir monitoreo** con Prometheus/Grafana
6. **Integrar observabilidad** con Sentry

---

## 💬 SOPORTE

Si algo falla durante deployment:

1. **Revisar logs:**
   ```bash
   docker-compose logs --tail=100
   ```

2. **Contactar:**
   - Issues: GitHub
   - Email: support@nexo.local
   - Discord: comunidad

---

**¡Felicidades! Tu sistema está online con dominio en < 1 hora.** 🎉

Ahora escala, optimiza y domina el futuro de la IA omnicanal.
