module.exports = {
  apps: [
    {
      name: "land-valuation-api",
      script: "uvicorn",
      args: "main:app --host 0.0.0.0 --port 8000 --workers 1",
      cwd: ".", 
      interpreter: "./venv/bin/python", 
      env: {
        NODE_ENV: "production",
      },
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    },
    {
      name: "celery-worker",
      script: "celery",
      args: "-A worker.worker worker --loglevel=info",
      cwd: ".",
      interpreter: "./venv/bin/python", // Point to your virtual env python
      env: {
        NODE_ENV: "production",
      },
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    }
  ]
};