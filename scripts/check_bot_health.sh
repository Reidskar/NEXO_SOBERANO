#!/bin/bash
# Health check for NEXO Voice Bot

echo "--- NEXO Voice Bot Health Check ---"

# 1. Check if Docker container is running (if using Docker)
if command -v docker &> /dev/null && [ "$(docker ps -q -f name=nexo-discord-bot)" ]; then
    echo "🟢 Docker: nexo-discord-bot is running."
else
    echo "🟡 Docker: nexo-discord-bot is NOT running (ignore if not using Docker)."
fi

# 2. Check PM2 (if using PM2)
if command -v pm2 &> /dev/null; then
    pm2 status nexo-discord-bot | grep -q "online"
    if [ $? -eq 0 ]; then
        echo "🟢 PM2: nexo-discord-bot is online."
    else
        echo "🔴 PM2: nexo-discord-bot is NOT online."
    fi
fi

# 3. Check FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo "🟢 FFmpeg: Installed."
else
    echo "🔴 FFmpeg: NOT found in PATH."
fi

# 4. Check .env variables
if [ -f "discord_bot/.env" ]; then
    echo "🟢 .env: File found."
    # Check for critical keys (without revealing them)
    grep -q "DISCORD_TOKEN=" discord_bot/.env && echo "   - DISCORD_TOKEN: Set"
    grep -q "OPENAI_API_KEY=" discord_bot/.env && echo "   - OPENAI_API_KEY: Set"
    grep -q "ELEVENLABS_API_KEY=" discord_bot/.env && echo "   - ELEVENLABS_API_KEY: Set"
else
    echo "🔴 .env: File NOT found in discord_bot/."
fi

echo "--- End of Report ---"
