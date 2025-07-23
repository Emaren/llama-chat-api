// /var/www/llama-chat-api/ecosystem.config.js
module.exports = {
  apps: [
    {
      // FastAPI gateway for the chat stack
      name: "llama-chat-api",
      cwd: "/var/www/llama-chat-api",

      // Use uvicorn from venv directly
      script: "venv/bin/uvicorn",
      args: "app.main:app --host 127.0.0.1 --port 8006",

      // Run as standalone binary
      interpreter: "none",
      exec_mode: "fork",

      env: {
        PYTHONUNBUFFERED: "1",
        OPENAI_API_KEY: process.env.OPENAI_API_KEY,
      }
    }
  ]
};
