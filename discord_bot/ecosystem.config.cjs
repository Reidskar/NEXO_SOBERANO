module.exports = {
  apps: [
    {
      name: 'nexo-discord-bot',
      script: 'bot.js',
      cwd: './discord_bot',
      env: {
        NODE_ENV: 'production',
      },
      restart_delay: 5000,
      max_restarts: 10,
      error_file: './logs/bot-error.log',
      out_file: './logs/bot-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss'
    }
  ]
};
