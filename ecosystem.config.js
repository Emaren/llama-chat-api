module.exports = {
  apps: [
    {
      name: 'llama-api',
      cwd: '/var/www/llama-chat-api',
      script: 'uvicorn',
      args: 'app.main:app --host 127.0.0.1 --port 8002',
      interpreter: 'python3',
      exec_mode: 'fork',
      env: {
        NODE_ENV: 'production',
      },
    },
  ],
};
