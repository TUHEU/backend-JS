#!/usr/bin/env bash
#
# update.sh — pull latest code, rebuild changed images, restart the
# stack with Docker Compose. Run this from inside backend-phase2/ on
# the VPS any time you've pushed new changes to the repo.
#
#   ./update.sh
#
# (Switched from PM2 to Docker — see update-pm2.sh if you ever want
# to go back to that approach instead.)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "==> Pulling latest changes"
git pull

echo "==> Building and restarting the stack"
# --build: rebuilds any image whose Dockerfile/requirements/code changed.
# -d: detached (keeps running after this script exits).
# Docker Compose only recreates containers whose config/image actually
# changed, so this is safe to run even when nothing changed.
docker compose up --build -d

echo "==> Done. Current status:"
docker compose ps
