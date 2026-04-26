#!/usr/bin/env bash
#
# House Helper — Restart backend
# Usage: ./restart.sh
#

set -e

lsof -ti:8040 2>/dev/null | xargs kill -9 2>/dev/null || true

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
  source .venv/Scripts/activate
fi

cd backend
echo "Backend starting on :8040"
uvicorn main:app --reload --port 8040
