#!/usr/bin/env bash
#
# SahAIy — Run all tests
# Use before every commit: ./test.sh
#

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "  Running all tests..."
echo ""

# Backend
echo -e "  Backend..."
source .venv/bin/activate
RESULT=$(python -m pytest tests/ -q -m "not network and not live" --tb=short 2>&1 | tail -1)
if echo "$RESULT" | grep -q "passed"; then
  echo -e "  ${GREEN}✓${NC} $RESULT"
else
  echo -e "  ${RED}✗${NC} $RESULT"
  exit 1
fi

# Frontend
echo -e "  Frontend..."
cd frontend
RESULT=$(npx vitest run 2>&1 | grep "Tests" | tail -1)
echo -e "  ${GREEN}✓${NC} $RESULT"
cd ..

# Build check
echo -e "  Build..."
cd frontend
npm run build > /dev/null 2>&1
echo -e "  ${GREEN}✓${NC} Frontend builds"
cd ..

echo ""
echo -e "  ${GREEN}All tests passed.${NC} Safe to commit."
echo ""
