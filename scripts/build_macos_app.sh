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
  echo "swiftc unavailable; Lumen.app packaging needs Xcode Command Line Tools." >&2
  exit 1
fi

ICON_SOURCE="$ROOT_DIR/assets/lumen-icon.png"
ICONSET_DIR="$ROOT_DIR/dist/helpers/Lumen.iconset"
if [ -f "$ICON_SOURCE" ] && command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
  rm -rf "$ICONSET_DIR"
  mkdir -p "$ICONSET_DIR"
  sips -z 16 16 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
  sips -z 32 32 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
  sips -z 32 32 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
  sips -z 64 64 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
  sips -z 128 128 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
  sips -z 256 256 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
  sips -z 256 256 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
  sips -z 512 512 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
  sips -z 512 512 "$ICON_SOURCE" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
  cp "$ICON_SOURCE" "$ICONSET_DIR/icon_512x512@2x.png"
  iconutil -c icns "$ICONSET_DIR" -o "$APP_DIR/Contents/Resources/Lumen.icns"
else
  echo "Icon tools unavailable; Lumen.app will use the default app icon." >&2
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
  <key>CFBundleIconFile</key>
  <string>Lumen</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>13.0</string>
  <key>NSMicrophoneUsageDescription</key>
  <string>Lumen uses the microphone for optional local voice commands.</string>
  <key>NSSpeechRecognitionUsageDescription</key>
  <string>Lumen uses speech recognition to turn your voice commands into local agent requests.</string>
  <key>NSAppleEventsUsageDescription</key>
  <string>Lumen can open apps and browser pages when you request desktop actions.</string>
</dict>
</plist>
PLIST

swiftc "$ROOT_DIR/lumen/ui/macos_window.swift" -O -o "$APP_DIR/Contents/MacOS/Lumen"
printf '%s\n' "$ROOT_DIR" > "$APP_DIR/Contents/Resources/repo-path.txt"

cat > "$APP_DIR/Contents/Resources/README.txt" <<README
Lumen.app is the native window for the local Lumen repository.

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
