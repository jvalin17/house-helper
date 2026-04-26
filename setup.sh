#!/usr/bin/env bash
#
# House Helper — One-click setup
# Run: curl -sSL <url>/setup.sh | bash
# Or:  ./setup.sh
#

set -e

echo ""
echo "  House Helper — Setting up your career copilot"
echo "  ─────────────────────────────────────────────"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
DIM='\033[2m'
NC='\033[0m'

step() { echo -e "${BLUE}→${NC} $1"; }
done_msg() { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${DIM}  $1${NC}"; }

# --- Check prerequisites ---
step "Checking prerequisites..."

# Python
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    version=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
      PYTHON="$cmd"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  echo "ERROR: Python 3.10+ is required but not found."
  echo ""
  echo "Install Python:"
  echo "  macOS:   brew install python@3.12"
  echo "  Ubuntu:  sudo apt install python3.12"
  echo "  Windows: https://www.python.org/downloads/"
  exit 1
fi
done_msg "Python: $($PYTHON --version)"

# Node
if ! command -v node &>/dev/null; then
  echo "ERROR: Node.js is required but not found."
  echo ""
  echo "Install Node.js:"
  echo "  macOS:   brew install node"
  echo "  Ubuntu:  sudo apt install nodejs npm"
  echo "  Windows: https://nodejs.org/"
  exit 1
fi
done_msg "Node.js: $(node --version)"

# npm
if ! command -v npm &>/dev/null; then
  echo "ERROR: npm is required but not found."
  exit 1
fi
done_msg "npm: $(npm --version)"

# --- Backend setup ---
echo ""
step "Setting up backend..."

if [ ! -d ".venv" ]; then
  $PYTHON -m venv .venv
  info "Created virtual environment"
fi

# Activate venv
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
  source .venv/Scripts/activate
fi

pip install -q -e ".[dev]" 2>&1 | tail -1
done_msg "Backend dependencies installed"

# --- Frontend setup ---
echo ""
step "Setting up frontend..."

cd frontend
npm install --silent 2>&1 | tail -1
cd ..
done_msg "Frontend dependencies installed"

# --- PDF export dependency (optional) ---
echo ""
step "Checking PDF export support..."

if command -v brew &>/dev/null; then
  if ! brew list pango &>/dev/null 2>&1; then
    info "Installing pango for PDF export..."
    brew install pango --quiet 2>&1 | tail -1
    done_msg "Pango installed"
  else
    done_msg "Pango already installed"
  fi
elif command -v apt &>/dev/null; then
  if ! dpkg -l libpango-1.0-0 &>/dev/null 2>&1; then
    info "Installing pango for PDF export..."
    sudo apt install -y libpango-1.0-0 libpangocairo-1.0-0 -qq 2>&1 | tail -1
    done_msg "Pango installed"
  else
    done_msg "Pango already installed"
  fi
else
  info "Skipping PDF support — install pango manually for PDF export"
  info "All other exports (DOCX, TXT, Markdown) work without it"
fi

# --- Run tests ---
echo ""
step "Running tests..."
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
TEST_RESULT=$(python -m pytest tests/ -q -m "not network" --tb=no 2>&1 | tail -1)
done_msg "Tests: $TEST_RESULT"

# --- Done ---
echo ""
echo "  ─────────────────────────────────────────────"
echo -e "  ${GREEN}Setup complete.${NC}"
echo ""
echo "  To start the app, run:"
echo ""
echo "    ./start.sh"
echo ""
echo "  Or manually:"
echo "    Terminal 1: source .venv/bin/activate && cd backend && uvicorn main:app --reload --port 8040"
echo "    Terminal 2: cd frontend && npm run dev"
echo ""
echo "  Then open http://localhost:5173"
echo ""
