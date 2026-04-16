module.exports = {
  apps: [
    {
      name: "nexo-discord-bot",
      script: "discord_bot/bot.js",
      cwd: "C:\\Users\\Admn\\Desktop\\NEXO_SOBERANO",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "300M",
      node_args: "--dns-result-order=ipv4first",
      env: {
        NODE_ENV: "production"
      }
    }
  ]
};
