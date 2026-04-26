#!/usr/bin/env bash
#
# House Helper — Reset for testing
# Clears DB, kills servers, restarts fresh
#
# Usage:
#   ./reset.sh          — clear DB + restart
#   ./reset.sh --db     — clear DB only (don't restart)
#   ./reset.sh --restart — restart only (keep DB)
#

set -e

DIM='\033[2m'
NC='\033[0m'
BLUE='\033[0;34m'

DB_PATH="$HOME/.house-helper/house-helper.db"

if [ "$1" != "--restart" ]; then
  if [ -f "$DB_PATH" ]; then
    rm -f "$DB_PATH"
    echo -e "${BLUE}→${NC} Database cleared"
  else
    echo -e "${DIM}  No database to clear${NC}"
  fi
  # Also clear exports
  rm -rf "$HOME/.house-helper/exports/" 2>/dev/null
  echo -e "${DIM}  Exports cleared${NC}"
fi

if [ "$1" = "--db" ]; then
  echo -e "${DIM}  Done. Restart the app to create a fresh DB.${NC}"
  exit 0
fi

# Kill existing processes
lsof -ti:8040 2>/dev/null | xargs kill -9 2>/dev/null || true
echo -e "${BLUE}→${NC} Port 8040 freed"

# Activate venv
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
  source .venv/Scripts/activate
fi

# Restart backend
cd backend
uvicorn main:app --reload --port 8040 &
cd ..

sleep 2
echo -e "${BLUE}→${NC} Backend running on :8040"
echo ""
echo "  Fresh DB will be created on first request."
echo "  Frontend should already be running (npm run dev)."
echo "  Open http://localhost:5173"
echo ""
