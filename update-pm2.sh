#!/usr/bin/env bash
#
# update.sh — pull latest code, install/update deps, restart all (PM2 version — kept for reference,
# services under PM2. Run this from inside backend-phase2/ on the VPS
# any time you've pushed new changes to the repo.
#
#   ./update.sh
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "==> Pulling latest changes"
git pull

echo "==> Setting up virtualenv (venv/)"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

echo "==> Installing/updating dependencies"
pip install --upgrade pip -q
for svc in api-gateway user-service itinerary-service recommendation-service; do
  echo "   - $svc"
  pip install -r "$svc/requirements.txt" -q
done

deactivate

echo "==> Reloading services with PM2"
if pm2 describe gt-api-gateway > /dev/null 2>&1; then
  # Already running — reload for zero-downtime restart.
  pm2 reload ecosystem.config.js
else
  # First run on this machine.
  pm2 start ecosystem.config.js
fi
pm2 save

echo "==> Done. Current status:"
pm2 status
