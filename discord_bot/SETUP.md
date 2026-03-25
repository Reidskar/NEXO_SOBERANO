# 🤖 NEXO Discord Bot - Guía de Configuración

## Descripción General

El bot de Discord NEXO es un asistente inteligente que se conecta a canales de voz, responde preguntas mediante integración con el backend NEXO_CORE y proporciona comandos slash para gestionar el sistema.

## Requisitos Previos

- **Node.js**: v18.0.0 o superior
- **npm**: v9.0.0 o superior
- **Discord Server**: Acceso a un servidor de Discord donde puedas agregar bots
- **Discord Developer Account**: Para crear y configurar la aplicación del bot

## Paso 1: Crear la Aplicación en Discord Developer Portal

### 1.1 Acceder al Developer Portal

1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Inicia sesión con tu cuenta de Discord
3. Haz clic en "New Application"
4. Ingresa un nombre (ej: "NEXO Bot")
5. Acepta los términos y crea la aplicación

### 1.2 Obtener el Client ID

1. En la página de la aplicación, ve a la sección "General Information"
2. Copia el valor de **APPLICATION ID** (este es tu `DISCORD_CLIENT_ID`)

### 1.3 Crear el Bot

1. Ve a la sección "Bot" en el menú izquierdo
2. Haz clic en "Add Bot"
3. Bajo el nombre del bot, haz clic en "Reset Token"
4. Copia el token (este es tu `DISCORD_TOKEN`)
5. **IMPORTANTE**: Guarda este token en un lugar seguro. No lo compartas públicamente.

### 1.4 Configurar Permisos

1. Ve a la sección "OAuth2" → "URL Generator"
2. Selecciona los scopes:
   - `bot`
   - `applications.commands`
3. Selecciona los permisos:
   - `Send Messages`
   - `Read Messages/View Channels`
   - `Connect`
   - `Speak`
   - `Use Voice Activity`
   - `Manage Messages`
4. Copia la URL generada y ábrela en tu navegador para agregar el bot a tu servidor

## Paso 2: Configurar Variables de Entorno

### 2.1 Crear archivo .env

1. En el directorio `discord_bot/`, copia `.env.example` a `.env`:

```bash
cp .env.example .env
```

### 2.2 Completar variables

Edita el archivo `.env` con tus valores:

```env
# Discord
DISCORD_TOKEN=tu_token_aqui
DISCORD_CLIENT_ID=tu_client_id_aqui

# NEXO Backend
NEXO_BACKEND=http://127.0.0.1:8000
NEXO_API_KEY=NEXO_LOCAL_2026_OK

# Opcionales
LOG_LEVEL=INFO
DEBUG=false
```

## Paso 3: Instalar Dependencias

```bash
cd discord_bot
npm install
```

### Dependencias Principales

| Paquete | Versión | Propósito |
|---------|---------|----------|
| discord.js | ^14.14.0 | Cliente de Discord |
| @discordjs/voice | ^0.16.1 | Soporte de voz |
| @discordjs/opus | ^0.9.0 | Codec de audio |
| dotenv | ^16.3.1 | Gestión de variables de entorno |
| axios | ^1.6.2 | Cliente HTTP |

## Paso 4: Iniciar el Bot

### Modo Producción

```bash
npm start
```

### Modo Desarrollo (con auto-reload)

```bash
npm run dev
```

### Esperado

Deberías ver algo como:

```
✅ Configuración cargada:
   - Backend: http://127.0.0.1:8000
   - Client ID: 123456789...

🔄 Registrando comandos slash...
✅ 5 comandos registrados exitosamente

🚀 Iniciando NEXO Discord Bot...

✅ Bot conectado como: NEXO#1234
📊 Servidores: 1
✅ Bot iniciado correctamente
```

## Comandos Disponibles

### /unirse

Conecta el bot a tu canal de voz actual.

```
/unirse
```

**Respuesta esperada**: "🎙️ **NEXO conectado a [nombre del canal]**"

### /salir

Desconecta el bot del canal de voz.

```
/salir
```

**Respuesta esperada**: "👋 **NEXO desconectado**"

### /nexo

Consulta una pregunta a NEXO y obtén una respuesta del backend.

```
/nexo pregunta: ¿Cuál es tu nombre?
```

**Respuesta esperada**: "🤖 **NEXO:** [respuesta del backend]"

### /estado

Muestra el estado actual del bot y del backend.

```
/estado
```

**Respuesta esperada**: Embed con estado de voz, backend, servidores y usuarios.

### /ayuda

Muestra la lista de comandos disponibles.

```
/ayuda
```

## Solución de Problemas

### Error: "DISCORD_TOKEN no está configurado"

**Solución**: Verifica que el archivo `.env` existe y contiene `DISCORD_TOKEN=tu_token_aqui`

### Error: "No tengo permiso para conectarme a este canal"

**Solución**: 
1. Ve a Discord Developer Portal
2. Selecciona tu aplicación
3. Ve a OAuth2 → URL Generator
4. Asegúrate de que los permisos `Connect` y `Speak` están seleccionados
5. Regenera la URL de invitación y vuelve a agregar el bot

### El bot no responde a comandos

**Solución**:
1. Verifica que los comandos slash están registrados: Deberías ver "✅ X comandos registrados" al iniciar
2. Intenta usar `/` en Discord para ver si aparecen los comandos
3. Si no aparecen, espera 1-2 minutos para que se sincronicen

### Error: "Backend error: 404"

**Solución**:
1. Verifica que NEXO_BACKEND está correcto en `.env`
2. Verifica que el backend NEXO_CORE está corriendo
3. Prueba la URL manualmente: `curl http://127.0.0.1:8000/health`

### El bot se desconecta de voz frecuentemente

**Solución**:
1. Verifica tu conexión a internet
2. Aumenta `VOICE_RECONNECT_SECONDS` en `.env`
3. Verifica que el bot tiene permisos de "Use Voice Activity"

## Estructura del Proyecto

```
discord_bot/
├── bot.js                 # Archivo principal del bot
├── package.json          # Dependencias
├── .env.example          # Plantilla de variables de entorno
├── .env                  # Variables de entorno (no compartir)
├── handlers/
│   ├── voiceHandler.js   # Manejo de conexiones de voz
│   └── apiHandler.js     # Comunicación con backend
├── SETUP.md              # Esta guía
└── README.md             # Documentación general
```

## Logs y Debugging

### Ver logs en tiempo real

```bash
npm start
```

### Habilitar modo debug

En `.env`:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

### Guardar logs en archivo

Los logs se guardan automáticamente en `nexo_bot.log`

```bash
tail -f nexo_bot.log
```

## Despliegue en Producción

### Usando PM2

```bash
# Instalar PM2 globalmente
npm install -g pm2

# Iniciar bot con PM2
pm2 start bot.js --name "nexo-discord-bot"

# Ver estado
pm2 status

# Ver logs
pm2 logs nexo-discord-bot

# Reiniciar
pm2 restart nexo-discord-bot

# Detener
pm2 stop nexo-discord-bot
```

### Usando Docker

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

CMD ["node", "bot.js"]
```

Construir y ejecutar:

```bash
docker build -t nexo-discord-bot .
docker run -d --env-file .env --name nexo-bot nexo-discord-bot
```

## Monitoreo

### Health Check

El bot realiza health checks automáticos al backend cada 30 segundos. Puedes ver el estado en los logs:

```
✅ Backend online
❌ Backend offline
```

### Métricas

El bot registra:
- Comandos ejecutados
- Errores y excepciones
- Cambios de estado de voz
- Conexiones y desconexiones

## Seguridad

### Mejores Prácticas

1. **Nunca compartas tu token**: El token es como una contraseña
2. **Usa variables de entorno**: No hardcodees credenciales
3. **Limita permisos**: Solo otorga los permisos necesarios
4. **Monitorea logs**: Busca actividades sospechosas
5. **Rota tokens regularmente**: Regenera el token cada 3 meses

### Si tu token fue comprometido

1. Ve a Discord Developer Portal
2. Selecciona tu aplicación
3. Ve a "Bot" → "Reset Token"
4. Copia el nuevo token
5. Actualiza `.env` con el nuevo token
6. Reinicia el bot

## Soporte y Contacto

Para reportar problemas o sugerencias:

1. Revisa los logs para mensajes de error
2. Verifica la sección de Solución de Problemas
3. Contacta al equipo de desarrollo

## Licencia

MIT - El Anarcocapital

---

**Última actualización**: Marzo 2026
**Versión**: 1.0.0
