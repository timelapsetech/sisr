# SISR for macOS (SwiftUI)

Native macOS app for rendering image sequences. Preview, crop, grade, and export with Core Image + AVFoundation.

## Requirements

- macOS 14 Sonoma or later
- Xcode 15+ (Xcode 16/27 recommended)
- Accept the Xcode license if prompted: `sudo xcodebuild -license accept`

## Open & run

Build and launch without opening the Xcode GUI (from the repo root):

```bash
make run-macos
```

Or from `macos/`:

```bash
./scripts/run-app.sh
```

This builds into `macos/.derivedData` and opens `SISR.app`. Re-run anytime after code changes.

To work in Xcode instead:

```bash
cd macos
python3 scripts/generate_xcodeproj.py   # regenerate project if sources change
open SISR.xcodeproj
```

In Xcode: select the **SISR** scheme → Run (⌘R).

### Package tests

```bash
cd macos/Packages/SISRKit
swift test
```

## Layout

| Path | Role |
|------|------|
| `SISR/` | SwiftUI app (three-panel UI, dark-mode theme) |
| `Packages/SISRKit/` | Sequence scanning, EXIF dates, crop/pipeline, AVFoundation/GIF render |
| `project.yml` | Optional XcodeGen spec (if you prefer `xcodegen generate`) |
| `scripts/generate_xcodeproj.py` | Checked-in generator for `SISR.xcodeproj` |

## Features

- Source / Output / Overlay sidebar (parity with the Python app’s render options)
- Center viewer + filmstrip timeline with in/out points, J/K/L, I/O
- Inspector: crop with aspect lock & resolution checks, transform, color, detail, deflicker
- Codecs: H.264, HEVC, ProRes, ProRes HQ, GIF
- Live render progress (sidebar card, toolbar, Dock badge, notification)
- Per-sequence state autosave; security-scoped bookmarks; Open Recent
- No batch subfolder rendering (configure one sequence per window)

## Release

See [../scripts/release/README.md](../scripts/release/README.md) and `.github/workflows/release-macos-swift.yml`.

Tag with `app-v*` (e.g. `app-v1.0.0`) to build, notarize, and attach a universal zip.
