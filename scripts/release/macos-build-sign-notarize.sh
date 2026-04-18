#!/usr/bin/env bash
# Build SISR.app with PyInstaller, optionally sign (Developer ID), notarize (App Store Connect API),
# and emit a release zip: SISR-<version>-macos-<arch>.zip
#
# Usage:
#   ./scripts/release/macos-build-sign-notarize.sh
#   SIGNING_IDENTITY="Developer ID Application: ..." ./scripts/release/macos-build-sign-notarize.sh --skip-notarize
#
# Environment (signing + notarization):
#   SIGNING_IDENTITY   Full codesign identity (recommended in CI after importing a .p12)
#   ENTITLEMENTS       Path to entitlements plist (default: resources/SISR.entitlements)
#   KEYCHAIN_PATH      Optional; CI temp keychain path
#   KEYCHAIN_PASSWORD  Optional; unlock password for KEYCHAIN_PATH
#
# Notarization (App Store Connect API key — recommended):
#   APPLE_API_KEY_ID, APPLE_API_ISSUER_ID, APPLE_API_KEY_PATH
#   (or APPLE_API_KEY_P8 with the private key contents for CI)
#
# See scripts/release/README.md for GitHub Actions secrets mapping.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

SKIP_SIGN=false
SKIP_NOTARIZE=false
PYTHON="${PYTHON:-python3}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-sign) SKIP_SIGN=true; shift ;;
    --skip-notarize) SKIP_NOTARIZE=true; shift ;;
    -h|--help)
      sed -n '1,25p' "$0"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

VERSION="$(grep -E '^version[[:space:]]*=' "$ROOT/pyproject.toml" | head -1 | sed -E 's/^version[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/')"
if [[ -z "$VERSION" ]]; then
  echo "Could not read version from pyproject.toml" >&2
  exit 1
fi
MACHINE="$(uname -m)"
case "$MACHINE" in
  arm64) ARCH_LABEL=arm64 ;;
  x86_64) ARCH_LABEL=x86_64 ;;
  *) ARCH_LABEL="$MACHINE" ;;
esac

ENTITLEMENTS="${ENTITLEMENTS:-$ROOT/resources/SISR.entitlements}"
APP_PATH="$ROOT/dist/SISR.app"
ZIP_NAME="SISR-${VERSION}-macos-${ARCH_LABEL}.zip"
SUBMIT_ZIP="$ROOT/dist/notary-submit-${ARCH_LABEL}.zip"

if [[ ! -f "$ENTITLEMENTS" ]]; then
  echo "Entitlements not found: $ENTITLEMENTS" >&2
  exit 1
fi

echo "==> Version $VERSION  arch $ARCH_LABEL  root $ROOT"

echo "==> Installing build dependencies"
"$PYTHON" -m pip install -U pip wheel
"$PYTHON" -m pip install -r "$ROOT/requirements.txt" -r "$ROOT/requirements-dev.txt"
"$PYTHON" -m pip install -e "$ROOT"
"$PYTHON" -c "import pkg_resources" 2>/dev/null || {
  echo "pkg_resources missing (needed by PyInstaller). Reinstalling setuptools..." >&2
  "$PYTHON" -m pip install --force-reinstall "setuptools>=69.0.0,<81.0.0"
}

echo "==> PyInstaller"
rm -rf "$ROOT/build" "$ROOT/dist"
"$PYTHON" -m PyInstaller --noconfirm "$ROOT/sisr.spec"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Expected app bundle at $APP_PATH" >&2
  exit 1
fi

if [[ "$SKIP_SIGN" == true ]]; then
  echo "==> Skipping codesign (--skip-sign)"
else
  if [[ -n "${KEYCHAIN_PATH:-}" && -n "${KEYCHAIN_PASSWORD:-}" ]]; then
    security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"
    security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH" || true
  fi

  if [[ -z "${SIGNING_IDENTITY:-}" ]]; then
    SIGNING_IDENTITY="$(
      security find-identity -v -p codesigning 2>/dev/null \
        | sed -n 's/.*"\(Developer ID Application:.*\)".*/\1/p' \
        | head -1
    )"
  fi

  if [[ -z "$SIGNING_IDENTITY" ]]; then
    echo "No SIGNING_IDENTITY and no Developer ID Application certificate in keychain." >&2
    echo "Pass SIGNING_IDENTITY or import a Developer ID .p12 (see scripts/release/README.md)." >&2
    exit 1
  fi

  echo "==> codesign: $SIGNING_IDENTITY"
  codesign --force --sign "$SIGNING_IDENTITY" --timestamp \
    --options runtime \
    --entitlements "$ENTITLEMENTS" \
    --deep \
    "$APP_PATH"

  codesign --verify --deep --strict --verbose=2 "$APP_PATH"
fi

if [[ "$SKIP_NOTARIZE" == true ]]; then
  echo "==> Skipping notarization (--skip-notarize)"
  if [[ "$SKIP_SIGN" == true ]]; then
    ZIP_NAME="SISR-${VERSION}-macos-${ARCH_LABEL}-unsigned.zip"
  fi
  ditto -c -k --keepParent "$APP_PATH" "$ROOT/dist/$ZIP_NAME"
  echo "==> Output: dist/$ZIP_NAME (not notarized)"
  exit 0
fi

if [[ "$SKIP_SIGN" == true ]]; then
  echo "Notarization requires a signed app. Omit --skip-sign or use --skip-notarize only." >&2
  exit 1
fi

# API key file for notarytool
API_KEY_PATH="${APPLE_API_KEY_PATH:-}"
if [[ -z "$API_KEY_PATH" && -n "${APPLE_API_KEY_P8:-}" ]]; then
  API_KEY_PATH="$ROOT/dist/AuthKey_notary.p8"
  printf '%s' "$APPLE_API_KEY_P8" > "$API_KEY_PATH"
  chmod 600 "$API_KEY_PATH"
fi

if [[ -z "$API_KEY_PATH" || -z "${APPLE_API_KEY_ID:-}" || -z "${APPLE_API_ISSUER_ID:-}" ]]; then
  echo "Notarization env not set. Need APPLE_API_KEY_ID, APPLE_API_ISSUER_ID, and APPLE_API_KEY_PATH" >&2
  echo "or APPLE_API_KEY_P8 (key contents). Use --skip-notarize for a local signed-only zip." >&2
  exit 1
fi

echo "==> Notary submit (zip)"
rm -f "$SUBMIT_ZIP"
ditto -c -k --keepParent "$APP_PATH" "$SUBMIT_ZIP"

xcrun notarytool submit "$SUBMIT_ZIP" \
  --key "$API_KEY_PATH" \
  --key-id "$APPLE_API_KEY_ID" \
  --issuer "$APPLE_API_ISSUER_ID" \
  --wait

echo "==> Staple"
xcrun stapler staple "$APP_PATH"

echo "==> Release zip (stapled app)"
rm -f "$ROOT/dist/$ZIP_NAME"
ditto -c -k --keepParent "$APP_PATH" "$ROOT/dist/$ZIP_NAME"

echo "==> Done: dist/$ZIP_NAME"
ls -la "$ROOT/dist/$ZIP_NAME"
