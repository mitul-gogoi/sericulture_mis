# Sericulture MIS

Web app for the Directorate of Sericulture, Government of Assam. See [CLAUDE.md](CLAUDE.md) for architecture, business rules, and day-to-day dev orientation; [memory/PRD.md](memory/PRD.md) for the full build history and backlog.

## Running locally (Windows)

1. Backend — PowerShell, from the project root, with the venv available:

To start:
& "backend\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8001 --app-dir backend

To stop:
press Ctrl+C once

If this does not work,
Get-NetTCPConnection -LocalPort 8001 -State Listen | Select-Object OwningProcess
Stop-Process -Id <that PID> -Force

2. Frontend — a separate terminal, from frontend/::

To start:
yarn build
yarn start

Then open http://localhost:3000 in your browser and log in.

To stop:
press Ctrl+C once

If this does not work,
Get-NetTCPConnection -LocalPort 3000 -State Listen | Select-Object OwningProcess
Stop-Process -Id <that PID> -Force

** CHECK **
Here are PowerShell commands you can run yourself anytime to find and kill whatever's on those ports:

Find what's using the ports:
Get-NetTCPConnection -LocalPort 8001,3000 -ErrorAction SilentlyContinue | Select-Object LocalPort, State, OwningProcess

Kill by port directly (one-liner, handles multiple PIDs):
Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

Or see the process name/details first before killing (safer if you want to confirm it's actually uvicorn/node):
Get-Process -Id (Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue).OwningProcess
Get-Process -Id (Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue).OwningProcess

Older netstat-based alternative (works even on systems without the NetTCPConnection cmdlets):
netstat -ano | findstr ":8001"
netstat -ano | findstr ":3000"

# then, using the PID from the last column:

Stop-Process -Id <PID> -Force
