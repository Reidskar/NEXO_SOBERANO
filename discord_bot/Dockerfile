FROM node:18-alpine

# Establecer directorio de trabajo
WORKDIR /app

# Copiar package.json y package-lock.json
COPY package*.json ./

# Instalar dependencias
RUN npm ci --only=production

# Copiar el código del bot
COPY . .

# Crear directorio de logs
RUN mkdir -p logs

# Comando para iniciar el bot
CMD ["node", "bot.js"]
