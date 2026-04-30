#!/usr/bin/env bash
#
# Panini — Start the app (backend + frontend)
# Usage: ./run.sh
#

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check if setup has been done
if [ ! -d ".venv" ]; then
  echo -e "${RED}Setup not done yet. Run ./setup.sh first.${NC}"
  exit 1
fi

if [ ! -d "frontend/node_modules" ]; then
  echo -e "${RED}Frontend not installed. Run ./setup.sh first.${NC}"
  exit 1
fi

echo ""
echo -e "  ${GREEN}Starting Panini...${NC}"
echo ""

# Start backend in background
source .venv/bin/activate
cd backend
uvicorn main:app --port 8040 --reload &
BACKEND_PID=$!
cd ..

# Start frontend in background
cd frontend
npx vite --host &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "  ${GREEN}App running:${NC}"
echo "    Frontend: http://localhost:5173"
echo "    Backend:  http://localhost:8040"
echo ""
echo "  Press Ctrl+C to stop both servers"
echo ""

# Handle Ctrl+C — kill both processes
trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

# Wait for either to exit
wait
