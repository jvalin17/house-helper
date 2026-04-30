#!/usr/bin/env bash
#
# Kaarsaaz — One-command setup
# Usage: ./setup.sh
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "  ${BLUE}>${NC} $1"; }
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
fail()  { echo -e "  ${RED}✗${NC} $1"; exit 1; }

echo ""
echo "  Kaarsaaz — Setup"
echo ""

# ── Python ──────────────────────────────────────────────

PYTHON=""
for cmd in python3.12 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    ver=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; then
      PYTHON="$cmd"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  fail "Python 3.10+ not found. Install Python 3.12: https://www.python.org/downloads/"
fi
ok "Python: $($PYTHON --version)"

# ── Node ────────────────────────────────────────────────

if ! command -v node &>/dev/null; then
  fail "Node.js not found. Install Node 18+: https://nodejs.org/"
fi

NODE_VER=$(node --version | grep -oE '[0-9]+' | head -1)
if [ "$NODE_VER" -lt 18 ]; then
  fail "Node 18+ required (found $(node --version))"
fi
ok "Node: $(node --version)"

# ── Backend venv + deps ─────────────────────────────────

if [ ! -d ".venv" ]; then
  info "Creating Python virtual environment..."
  $PYTHON -m venv .venv
fi
source .venv/bin/activate
ok "Virtual environment: .venv"

info "Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet \
  fastapi uvicorn python-dotenv httpx \
  anthropic openai \
  rapidfuzz python-docx pdfplumber \
  python-multipart reportlab docx2pdf \
  "numpy<2" "transformers<5"
pip install --quiet -e ".[dev]"
ok "Python packages installed"

# Optional: sentence-transformers + spaCy (for offline matching)
if pip show sentence-transformers &>/dev/null; then
  ok "Sentence Transformers already installed"
else
  info "Installing offline ML models (optional, ~500MB)..."
  pip install --quiet "sentence-transformers>=3.0" "spacy>=3.7" 2>/dev/null || {
    echo -e "  ${BLUE}>${NC} Skipped — install manually with: pip install sentence-transformers spacy"
  }
fi

# ── Frontend deps ───────────────────────────────────────

info "Installing frontend dependencies..."
cd frontend
npm install --silent 2>/dev/null
ok "Frontend packages installed"
cd ..

# ── .env ────────────────────────────────────────────────

if [ ! -f ".env" ]; then
  cp .env.example .env
  info "Created .env from template — add your API keys there"
else
  ok ".env exists"
fi

# ── Done ────────────────────────────────────────────────

echo ""
echo -e "  ${GREEN}Setup complete.${NC}"
echo ""
echo "  To start the app:"
echo ""
echo "    # Terminal 1 — Backend"
echo "    source .venv/bin/activate"
echo "    uvicorn backend.main:app --port 8040 --reload"
echo ""
echo "    # Terminal 2 — Frontend"
echo "    cd frontend && npm run dev"
echo ""
echo "  Then open http://localhost:5173"
echo ""
