#!/usr/bin/env bash
# Downloads the official AgiBot D1 Ultra URDF + STL meshes.
# Source: https://www.agibot.com.cn/filepage/329.html
# License: NOT DECLARED by AgiBot — for demo/internal use only. Do not redistribute.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/web/public/d1"
URL="https://www.agibot.com.cn/file/ueditor/php/upload/file/20260414/1776129631198724.zip"
TMP="$(mktemp -d)"

echo "Downloading D1 Ultra URDF from AgiBot..."
if ! curl -fL --connect-timeout 20 --max-time 120 -o "$TMP/d1.zip" "$URL"; then
  echo "WARN: download failed. Procedural robot fallback will be used."
  exit 0
fi

mkdir -p "$DEST"
unzip -qo "$TMP/d1.zip" -d "$TMP/extracted"

# Layout expected by the web loader: public/d1/urdf/ultra.urdf + public/d1/meshes/*.STL
if [ -d "$TMP/extracted/ultra_description" ]; then
  mkdir -p "$DEST/urdf" "$DEST/meshes"
  cp "$TMP/extracted/ultra_description/urdf/"*.urdf "$DEST/urdf/" 2>/dev/null || true
  cp "$TMP/extracted/ultra_description/meshes/"*.STL "$DEST/meshes/" 2>/dev/null || true
  cp "$TMP/extracted/ultra_description/meshes/"*.stl "$DEST/meshes/" 2>/dev/null || true
  # Fix mesh paths in URDF to ../meshes/
  if [ -f "$DEST/urdf/ultra.urdf" ]; then
    # leave relative ../meshes/ as-is if already correct
    echo "Installed to $DEST"
    ls -la "$DEST/urdf" "$DEST/meshes" | head -40
  fi
else
  echo "WARN: unexpected zip layout. Contents:"
  find "$TMP/extracted" -maxdepth 3 -type f | head -40
fi

rm -rf "$TMP"
echo "Done. If meshes are missing, the app uses the procedural D1 fallback."
