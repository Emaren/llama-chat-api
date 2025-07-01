module.exports = {
  apps: [
    {
      name: "llama-chat-api",
      script: "./venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 8006",
      cwd: "/var/www/llama-chat-api",
      interpreter: "none"
    }
  ]
}
