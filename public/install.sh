#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${LUMEN_DIR:-$HOME/Documents/Code/Lumen}"
REPO_URL="https://github.com/OmTheLast/Lumen.git"

echo "Lumen installer"
echo "Target: $TARGET_DIR"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required. Install Xcode Command Line Tools first:"
  echo "  xcode-select --install"
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it from https://docs.astral.sh/uv/ before continuing."
  echo "One common install command is:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

mkdir -p "$(dirname "$TARGET_DIR")"

if [ -d "$TARGET_DIR/.git" ]; then
  echo "Existing Lumen checkout found. Pulling latest changes."
  git -C "$TARGET_DIR" pull --ff-only
else
  echo "Cloning Lumen."
  git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"
uv sync

cat <<'NEXT'

Lumen is installed.

Start it with:
  cd ~/Documents/Code/Lumen && uv run python -m lumen.main

Then open:
  http://127.0.0.1:8765

Optional local models:
  ollama pull qwen3:latest

Optional voice dependencies:
  uv sync --extra voice
NEXT
