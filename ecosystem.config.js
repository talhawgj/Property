module.exports = {
  apps: [
    {
      name: "land-valuation-api",
      script: "/home/devuser/Parcel/venv/bin/uvicorn",
      args: "main:app --host 0.0.0.0 --port 8001 --workers 1",
      cwd: "/home/devuser/Parcel/Property",
      env: {
        NODE_ENV: "production",
      },
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    }
  ]
};