#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Lumen"
APP_DIR="$ROOT_DIR/dist/macos/$APP_NAME.app"
INSTALL_TARGET=""

usage() {
  cat <<'USAGE'
Build the Lumen macOS app wrapper.

Usage:
  scripts/build_macos_app.sh [--install-user|--install-system]

Options:
  --install-user    Copy Lumen.app to ~/Applications
  --install-system  Copy Lumen.app to /Applications
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --install-user)
      INSTALL_TARGET="$HOME/Applications"
      ;;
    --install-system)
      INSTALL_TARGET="/Applications"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Lumen.app packaging is only supported on macOS." >&2
  exit 1
fi

mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"
mkdir -p "$ROOT_DIR/dist/helpers"

if command -v swiftc >/dev/null 2>&1; then
  swiftc "$ROOT_DIR/lumen/ui/macos_window.swift" -O -o "$ROOT_DIR/dist/helpers/lumen-window"
  swiftc "$ROOT_DIR/lumen/ui/macos_overlay.swift" -O -o "$ROOT_DIR/dist/helpers/lumen-overlay"
else
  echo "swiftc unavailable; native Lumen window and AppKit orb helper will be skipped." >&2
fi

cat > "$APP_DIR/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>Lumen</string>
  <key>CFBundleDisplayName</key>
  <string>Lumen</string>
  <key>CFBundleIdentifier</key>
  <string>com.ompatnaik.lumen</string>
  <key>CFBundleVersion</key>
  <string>0.3.0</string>
  <key>CFBundleShortVersionString</key>
  <string>0.3.0</string>
  <key>CFBundleExecutable</key>
  <string>Lumen</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>13.0</string>
  <key>NSMicrophoneUsageDescription</key>
  <string>Lumen uses the microphone for optional local voice commands.</string>
  <key>NSAppleEventsUsageDescription</key>
  <string>Lumen can open apps and browser pages when you request desktop actions.</string>
</dict>
</plist>
PLIST

cat > "$APP_DIR/Contents/MacOS/Lumen" <<LAUNCHER
#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:\$PATH"
export LUMEN_REPO_DIR="\${LUMEN_REPO_DIR:-$ROOT_DIR}"
export LUMEN_UI_OPEN_BROWSER="\${LUMEN_UI_OPEN_BROWSER:-0}"
export LUMEN_APP_WINDOW_ENABLED="\${LUMEN_APP_WINDOW_ENABLED:-1}"
export LUMEN_OVERLAY_ENABLED="\${LUMEN_OVERLAY_ENABLED:-1}"

LOG_DIR="\$HOME/Library/Logs/Lumen"
mkdir -p "\$LOG_DIR"

if ! command -v uv >/dev/null 2>&1; then
  osascript -e 'display dialog "Lumen needs uv. Install it from https://docs.astral.sh/uv/ and run the installer again." buttons {"OK"} default button "OK" with icon caution' >/dev/null 2>&1 || true
  exit 127
fi

cd "\$LUMEN_REPO_DIR"
exec uv run python -m lumen.main --app >> "\$LOG_DIR/lumen.log" 2>&1
LAUNCHER

chmod +x "$APP_DIR/Contents/MacOS/Lumen"

cat > "$APP_DIR/Contents/Resources/README.txt" <<README
Lumen.app is a launcher wrapper around the local Lumen repository.

Repository:
$ROOT_DIR

Logs:
~/Library/Logs/Lumen/lumen.log

The app starts Lumen in app mode, opens the native Lumen window, and keeps the
agent running without terminal stdin. The interface is served locally by the
embedded server.
README

echo "Built $APP_DIR"

if [ -n "$INSTALL_TARGET" ]; then
  mkdir -p "$INSTALL_TARGET"
  rm -rf "$INSTALL_TARGET/$APP_NAME.app"
  cp -R "$APP_DIR" "$INSTALL_TARGET/$APP_NAME.app"
  echo "Installed $INSTALL_TARGET/$APP_NAME.app"
fi
