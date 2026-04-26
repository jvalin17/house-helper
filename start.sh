#!/usr/bin/env bash
#
# House Helper — Start the app
# Run: ./start.sh
#

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
DIM='\033[2m'
NC='\033[0m'

echo ""
echo -e "  ${BLUE}House Helper${NC} — Starting..."
echo ""

# Kill existing processes on our ports
lsof -ti:8040 2>/dev/null | xargs kill -9 2>/dev/null || true

# Activate venv
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
  source .venv/Scripts/activate
else
  echo "ERROR: Virtual environment not found. Run ./setup.sh first."
  exit 1
fi

# Start backend in background
cd backend
uvicorn main:app --port 8040 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo -e "  ${DIM}Starting backend on port 8040...${NC}"
for i in {1..10}; do
  if curl -s http://localhost:8040/health > /dev/null 2>&1; then
    break
  fi
  sleep 1
done
echo -e "  ${GREEN}✓${NC} Backend ready"

# Start frontend
echo -e "  ${DIM}Starting frontend...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

sleep 2
echo ""
echo -e "  ${GREEN}✓${NC} App is running"
echo ""
echo "  Open: http://localhost:5173"
echo ""
echo "  Press Ctrl+C to stop"
echo ""

# Handle cleanup on exit
cleanup() {
  echo ""
  echo -e "  ${DIM}Shutting down...${NC}"
  kill $BACKEND_PID 2>/dev/null || true
  kill $FRONTEND_PID 2>/dev/null || true
  echo -e "  ${GREEN}✓${NC} Stopped"
}
trap cleanup EXIT

# Wait for either process to exit
wait
