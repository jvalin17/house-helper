#!/usr/bin/env bash
#
# SahAIy — Build desktop app (PyInstaller + Tauri)
#

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "  ${BLUE}>${NC} $1"; }
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }

echo ""
echo "  Building SahAIy desktop app..."
echo ""

# ── Step 1: Build Python backend binary ──────

info "Building backend binary with PyInstaller..."
source .venv/bin/activate
cd backend
pyinstaller --onefile \
  --name sahaiy-backend \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.lifespan.on \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.loops.auto \
  --add-data "shared/ats_rules.json:shared" \
  main.py
cd ..

# Copy to Tauri binaries dir
ARCH=$(rustc -Vv | grep host | cut -d' ' -f2)
mkdir -p src-tauri/binaries
cp backend/dist/sahaiy-backend "src-tauri/binaries/sahaiy-backend-${ARCH}"
ok "Backend binary: src-tauri/binaries/sahaiy-backend-${ARCH}"

# ── Step 2: Build frontend ───────────────────

info "Building frontend..."
cd frontend
npm run build
cd ..
ok "Frontend: frontend/dist/"

# ── Step 3: Build Tauri app ──────────────────

info "Building Tauri app..."
cd frontend
npx tauri build
cd ..

echo ""
echo -e "  ${GREEN}Build complete!${NC}"
echo "  Output: src-tauri/target/release/bundle/"
echo ""
