# macOS release builds (PyInstaller + signing + notarization)

This folder contains `macos-build-sign-notarize.sh`, which:

1. Installs dependencies and runs **PyInstaller** using `sisr.spec`.
2. **Codesigns** `dist/SISR.app` with a **Developer ID Application** identity (hardened runtime + `resources/SISR.entitlements`).
3. **Submits** the app to Apple **notarization** via `notarytool` (App Store Connect API key).
4. **Staples** the ticket and writes `dist/SISR-<version>-macos-<arch>.zip` for distribution.

Architecture (`arm64` vs `x86_64`) comes from the machine that runs the script; use separate machines or CI matrix rows for each.

## One-time Apple setup

1. **Apple Developer Program** membership.
2. **Developer ID Application** certificate  
   Xcode → Settings → Accounts → Manage Certificates → Developer ID Application.  
   Export as `.p12` (remember the export password) for CI, or rely on your login keychain locally.
3. **App Store Connect API key** for notarization (recommended by Apple for automation)  
   [App Store Connect](https://appstoreconnect.apple.com/) → Users and Access → Integrations → **Keys** → generate an **App Manager** (or **Developer**) key.  
   Download the `.p8` file once; note **Key ID** and **Issuer ID** (UUID on the same page).

## GitHub repository secrets (tag releases)

Create these in **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
|--------|---------|
| `MACOS_CERTIFICATE_BASE64` | Base64-encoded `.p12` (see below) |
| `MACOS_CERTIFICATE_PASSWORD` | Password for that `.p12` |
| `APPLE_ASC_API_KEY_P8_BASE64` | Base64-encoded contents of the `.p8` API key file |
| `APPLE_ASC_API_KEY_ID` | Key ID (10 characters) |
| `APPLE_ASC_ISSUER_ID` | Issuer UUID from App Store Connect |

Encode files for secrets:

```bash
base64 -i Certificate.p12 | pbcopy   # paste into MACOS_CERTIFICATE_BASE64
base64 -i AuthKey_XXXXXXXX.p8 | pbcopy
```

## Publishing a release

1. Bump the version in `pyproject.toml` (and keep `sisr.spec` / bundle plist in sync if you track them there).
2. Commit and push a **version tag**:

   ```bash
   git tag v0.3.1
   git push origin v0.3.1
   ```

3. The workflow **Release (macOS)** (`.github/workflows/release-macos.yml`) builds on **macos-13** (Intel) and **macos-14** (Apple Silicon), uploads two zips, and attaches them to the GitHub **Release** for that tag.

You can also run **Actions → Release (macOS) → Run workflow** to produce **unsigned** zips (no secrets) for debugging; they are available as workflow artifacts only, not attached to a release.

## Local build (your Mac)

With Developer ID already in your login keychain and API key on disk:

```bash
export APPLE_API_KEY_ID="XXXXXXXXXX"
export APPLE_API_ISSUER_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export APPLE_API_KEY_PATH="$HOME/private/AuthKey_XXX.p8"
./scripts/release/macos-build-sign-notarize.sh
```

For a quick unsigned zip (no signing/notarization):

```bash
./scripts/release/macos-build-sign-notarize.sh --skip-sign --skip-notarize
```

Override Python: `PYTHON=/path/to/python3 ./scripts/release/...`

## Runner labels

GitHub occasionally changes which `macos-*` images map to Intel vs Apple Silicon. If a job fails or shows the wrong architecture, update the `matrix.runner` values in `release-macos.yml` to match [GitHub’s current hosted runners](https://docs.github.com/en/actions/using-github-hosted-runners/using-github-hosted-runners/about-github-hosted-runners#supported-runners-and-hardware-resources).

## Troubleshooting

- **codesign / notary failures**: Open the log on the failing step; `notarytool log --uuid ...` for detail.
- **Hardened runtime / PyInstaller**: If Apple rejects the bundle, you may need to adjust `resources/SISR.entitlements` (keep changes minimal and document why).
- **Icon**: `resources/icon.icns` and `resources/icons/` are bundled via `sisr.spec`. Regenerate with `python3 resources/create_icon.py` (macOS; requires Xcode command-line tools for `.icns`).
