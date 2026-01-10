module.exports = {
  apps: [
    {
      name: "land-valuation-api",
      script: "/home/devuser/Parcel/venv/bin/python",
      args: "-m uvicorn main:app --host 0.0.0.0 --port 8001 --workers 1",
      cwd: "/home/devuser/Parcel/Property",
      interpreter: "none",
      env: {
        NODE_ENV: "production",
      },
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    },
    {
      name: "dashboard-app",
      script: "npm",
      args: "start",
      cwd: "./dashboard",
      env: {
        NODE_ENV: "production",
        PORT: "4173",
      },
      error_file: "~/.pm2/logs/dashboard-app-error.log",
      out_file: "~/.pm2/logs/dashboard-app-out.log",
      merge_logs: true,
    },
  ]
};