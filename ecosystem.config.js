module.exports = {
  apps: [
    {
      name: "land-valuation-api",
      script: "/home/devuser/Parcel/venv/bin/python",
      args: "-m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1",
      cwd: "/home/devuser/Parcel/Property",
      interpreter: "none",
      env: {
        NODE_ENV: "production",
      },
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    }
  ]
};