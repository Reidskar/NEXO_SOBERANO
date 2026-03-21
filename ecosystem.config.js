// ============================================================
// NEXO SOBERANO — PM2 Ecosystem Config
// © 2026 elanarcocapital.com
// ============================================================
module.exports = {
  apps: [
    {
      name: "nexo-discord-bot",
      script: "discord_bot/bot.js",
      cwd: "C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO",
      watch: false,
      restart_delay: 5000,
      max_restarts: 10,
      env: {
        NODE_ENV: "production"
      }
    }
  ]
}
