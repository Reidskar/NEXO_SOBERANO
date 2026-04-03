// ============================================================
// NEXO SOBERANO — PM2 Ecosystem Config
// © 2026 elanarcocapital.com
// ============================================================
module.exports = {
  apps: [
    {
      name: "nexo-bot",
      script: "discord_bot/bot.js",
      cwd: "C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO",
      watch: false,
      restart_delay: 5000,
      max_restarts: 10,
      env: { NODE_ENV: "production" }
    },
    {
      name: "crucix-intel",
      script: "server.mjs",
      cwd: "C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO\\crucix_intel",
      watch: false,
      restart_delay: 10000,
      max_restarts: 5,
      env: { NODE_ENV: "production", PORT: "3117" }
    },
    {
      name: "nexo-api",
      script: ".venv\\Scripts\\uvicorn.exe",
      args: "backend.main:app --host 0.0.0.0 --port 8000",
      cwd: "C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO",
      interpreter: "none",
      watch: false,
      restart_delay: 5000,
      max_restarts: 10,
      autorestart: true,
      env: {
        NODE_ENV: "production",
        PORT: "8000"
      }
    },
    {
      name: "public-site",
      script: "cmd.exe",
      args: "/c node_modules\\.bin\\vite.cmd preview --port 8001 --host 0.0.0.0",
      cwd: "C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO\\public_site",
      interpreter: "none",
      watch: false,
      restart_delay: 5000,
      max_restarts: 10,
      autorestart: true,
      env: { NODE_ENV: "production" }
    },
    {
      name: "mcp-gateway",
      script: "cmd.exe",
      args: "/c docker mcp gateway run --transport=streaming --port=3200 --long-lived",
      cwd: "C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO",
      interpreter: "none",
      watch: false,
      restart_delay: 15000,
      max_restarts: 5,
      autorestart: true,
      env: {
        NODE_ENV: "production",
        MCP_GATEWAY_AUTH_TOKEN: "nexo_mcp_2026_secure",
        DISCORD_TOKEN: process.env.DISCORD_TOKEN || ""
      }
    }
  ]
}
