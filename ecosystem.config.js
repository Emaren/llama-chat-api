module.exports = {
  apps: [
    {
      /* FastAPI → Ollama gateway */
      name: "llama-api",
      cwd: "/var/www/llama-chat-api",

      /* use the Uvicorn binary from the venv */
      script: "venv/bin/uvicorn",

      /* IMPORTANT: app.main (not just main) to reflect app/main.py */
      args: "app.main:app --host 127.0.0.1 --port 8002",

      /* use the Python interpreter from the venv */
      interpreter: "./venv/bin/python",

      exec_mode: "fork",
      env: {
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};
