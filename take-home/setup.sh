#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Valkai Take-Home Setup ==="
echo ""

# --- mise ---
if command -v mise &>/dev/null; then
  echo "[ok] mise already installed"
else
  echo "[..] Installing mise..."
  curl -fsSL https://mise.run | sh
  export PATH="$HOME/.local/bin:$PATH"
  echo "[ok] mise installed"
fi

# Activate mise for this script
eval "$(mise activate bash --shims)"

# Trust this project's mise config
mise trust "$SCRIPT_DIR" 2>/dev/null || true

# Install mise-managed tools (node 22)
echo "[..] Installing mise tools (node)..."
mise install
echo "[ok] mise tools ready"

# --- uv (Python package manager) ---
if command -v uv &>/dev/null; then
  echo "[ok] uv already installed"
else
  echo "[..] Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  echo "[ok] uv installed"
fi

# --- Backend deps ---
echo "[..] Installing BE dependencies..."
(cd BE && uv sync)
echo "[ok] BE dependencies installed"

# --- Backend migrations ---
echo "[..] Running DB migrations..."
(cd BE && uv run python manage.py migrate --run-syncdb)
echo "[ok] DB ready"

# --- Frontend deps ---
echo "[..] Installing FE dependencies..."
(cd FE && npm install)
echo "[ok] FE dependencies installed"

echo ""
echo "=== Setup complete ==="
echo ""
echo "To start the app:"
echo "  cd $(basename "$SCRIPT_DIR")"
echo "  mise run dev"
echo ""
echo "This starts:"
echo "  BE  ->  http://localhost:8000"
echo "  FE  ->  http://localhost:5173"
