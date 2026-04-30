#!/usr/bin/env bash
#
# SahAIy — Set up Tauri desktop development
# Run this once to install Rust + Tauri CLI
#

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "  ${BLUE}>${NC} $1"; }
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
fail()  { echo -e "  ${RED}✗${NC} $1"; exit 1; }

echo ""
echo "  SahAIy — Tauri Setup"
echo ""

# ── Step 1: Rust ─────────────────────────────

if command -v rustc &>/dev/null; then
  ok "Rust: $(rustc --version)"
else
  info "Installing Rust..."
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  source "$HOME/.cargo/env"
  ok "Rust: $(rustc --version)"
fi

# ── Step 2: Tauri CLI ────────────────────────

if command -v cargo-tauri &>/dev/null; then
  ok "Tauri CLI installed"
else
  info "Installing Tauri CLI..."
  cargo install tauri-cli
  ok "Tauri CLI installed"
fi

# ── Step 3: System deps (macOS) ──────────────

if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS needs Xcode command line tools
  if ! xcode-select -p &>/dev/null; then
    info "Installing Xcode command line tools..."
    xcode-select --install
  fi
  ok "macOS deps ready"
fi

# ── Step 4: Initialize Tauri project ─────────

if [ ! -d "src-tauri" ]; then
  info "Initializing Tauri project..."
  cd frontend
  npm install -D @tauri-apps/cli@latest
  npm install @tauri-apps/api@latest
  npx tauri init --ci \
    --app-name "SahAIy" \
    --window-title "SahAIy" \
    --dist-dir "../frontend/dist" \
    --dev-url "http://localhost:5173" \
    --before-dev-command "" \
    --before-build-command "npm run build"
  cd ..
  ok "Tauri project initialized at src-tauri/"
else
  ok "src-tauri/ already exists"
fi

# ── Step 5: PyInstaller ──────────────────────

source .venv/bin/activate 2>/dev/null || true
if pip show pyinstaller &>/dev/null; then
  ok "PyInstaller installed"
else
  info "Installing PyInstaller..."
  pip install pyinstaller
  ok "PyInstaller installed"
fi

echo ""
echo -e "  ${GREEN}Tauri setup complete.${NC}"
echo ""
echo "  Development:"
echo "    Terminal 1: cd backend && uvicorn main:app --port 8040 --reload"
echo "    Terminal 2: cd frontend && cargo tauri dev"
echo ""
echo "  Production build:"
echo "    ./scripts/build-app.sh"
echo ""
