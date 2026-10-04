# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.3] - 2026-10-04

### Added
- **Native size** and **Scale to fit** full-frame shortcuts: render at source pixels, or shrink the full frame to a max width/height with no cropping.
- **Transform 90° chips** (0° / 90° / 180° / 270°) plus free **Angle** entry for any degree of fine rotation.
- **Overlay burn-in preview** inside the crop on the viewer, plus a **Background** opacity control (default 50%) that matches the final encode.
- **Preview full** at the top of the inspector: aspect-fits the cropped output (with burn-in) as large as possible in the viewer so you can inspect what the encode will look like.
- **Timeline zoom** — fit-by-default filmstrip with pinch / − Fit + controls; zoomed-out views sample frames so thumbs stay readable; zoom in to scroll frame-by-frame.
- **Go to Start / In / Out / End** transport controls (Home, ⇧I, ⇧O, End).
- **Play In to Out** (⇧Space) to preview only the marked range.
- **J / K / L** shuttle reverse, stop, and shuttle forward (repeat J/L to speed up).

### Changed
- **Play** runs the full sequence from the current playhead and ignores In/Out; at the last frame it wraps to the start.
- **Output size** lives entirely in the right inspector (all presets); the left Format section was removed.
- **Render destination** no longer defaults to the image-sequence folder; if unset, Render prompts for an output folder first.
- **Scale to fit** never upscales — max width/height act as a ceiling only.
- **Viewer playback** uses cached downscaled frames while playing (with forward prefetch) and applies the full graded preview when paused; playhead autosave and filmstrip decode are skipped during play for smoother scrubbing.

### Fixed
- **90° / 270° preview stretch** — viewer and crop overlay now fit the oriented (swapped) frame instead of the original landscape size.
- **Overlay background opacity** in renders now matches the viewer preview (transparent plate was blending against an uncleared buffer and looking too light).
- **Crop-mode crash** when source size was invalid (NaN → Int) — geometry helpers now harden zero/invalid sizes.

## [1.0.2] - 2026-10-03

### Added
- **App Store promotional screenshots** in `docs/assets/appstore/promo/`: captioned 2880×1800 / 2560×1600 / 1440×900 canvases (hero, preview, grade, export, workflow) generated from live UI captures, plus `generate_promo.py` to regenerate.

## [1.0.1] - 2026-10-03

### Added
- **Docs site for the native Mac app**: homepage with live UI screenshots, detailed `macos-guide.html`, App Store–oriented `privacy.html` / `support.html`, and marketing canvases under `docs/assets/appstore/`.
- **App Store compliance**: `ITSAppUsesNonExemptEncryption`, `PrivacyInfo.xcprivacy` (UserDefaults + file timestamps), Help menu and Settings links to guide / support / privacy.
- **Open / Close** in the sequence sidebar, plus clearer empty-state flow.
- **Numeric fields** alongside straighten and color sliders for precise values.
- **Bitrate & quality** progressive disclosure with auto Mbps targets for 1080p / 4K and manual overrides.
- **Settings toggle** for “Notify when render finishes” (permission requested at most once).

### Changed
- **Inspector progressive disclosure**: color adjustments grouped under one disclosure; align/zoom, resolution fitness, flips, and sharpen/noise/vignette stay collapsed until needed.
- **H.264 bitrate ladder** and encode path tuned for Instagram-friendly quality without excessive render memory use.
- **Deflicker analysis** reports per-frame progress instead of appearing stuck at 0%.

### Fixed
- **Straighten** preview vs render sign mismatch (Core Image rotation direction).
- **Sandbox overwrite / remove** failures when replacing an existing render (security-scoped bookmarks and unique sibling fallback).
- **FrameCache QoS** priority inversions that could stall preview decode under load.
- **Upscale / resolution fitness** warnings when output exceeds native crop coverage.
- **CLI `--open` / bare-path open** limited to Debug builds so Release/App Store sandboxed launches rely on Open panel / Finder.

## [1.0.0] - 2026-10-03

### Added
- **Native macOS app (SwiftUI)** in `macos/`: three-panel layout with scrubbable preview, timeline in/out points, interactive crop/transform/color, and Core Image + AVFoundation/GIF export (no FFmpeg). Dark-mode-first UI. See `macos/README.md`.
- **Swift release pipeline**: `.github/workflows/release-macos-swift.yml` and `scripts/release/macos-swift-build-sign-notarize.sh` for `app-v*` tags.

### Changed
- Python CLI/GUI remain available unchanged alongside the new native app.

## [0.6.0] - 2026-09-29
### Added
- **Date overlay parts (GUI)**: When Overlay is set to Date, checkboxes for Day, Month, Date, Year, and Time let you show or hide each component. Choices are saved in preferences. Overlay text reflows for any combination and scales down to fit the selected crop width.

## [0.5.1] - 2026-09-07
### Fixed
- **Input folder with a trailing slash**: Rendering a folder path ending in `/` produced a nameless output file (for example `.mp4_1920x1280`) and failed in FFmpeg. Folder paths are now normalized in the GUI and CLI, and an output file without a name or extension raises a clear error instead of reaching FFmpeg.

## [0.5.0] - 2026-08-15
### Added
- **Cancel rendering**: Stop an in-progress job from the GUI (Cancel button, File → Cancel Rendering, or Ctrl+.).
- **Skip invalid folders in batches**: Folders without a processable numbered sequence (gaps, a single still, unmatched names) are skipped and listed in a summary instead of aborting the whole run — GUI and CLI.

### Changed
- **PyQt6 GUI**: Replaced the Tkinter window with a native-style Qt interface and a clearer rendering progress layout.
- **Sequence detection**: Image folders must contain at least two consecutive numbered frames (for example `img_0001.jpg`, `img_0002.jpg`) that FFmpeg can read as a sequence.

## [0.4.2] - 2026-06-07
### Added
- **Frame rate in GUI**: Configurable output frame rate (default **30 fps**); the value is saved in preferences and applied to every output format (MP4, MOV, ProRes, GIF).
- **CLI `--framerate` alias**: `--framerate` is accepted as an alias for `--fps` when setting output frame rate.

### Changed
- The GUI no longer hardcodes 30 fps when rendering; it uses the frame rate from the window (or saved preference).

## [0.4.1] - 2026-04-19
### Fixed
- **Date overlay + max width/height**: Date text no longer renders extremely small when scaling with max width/height; scaling is applied before `drawtext`, consistent with the frame overlay path.
### Changed
- **Release / notarization**: `notarytool submit --wait` now uses a bounded wait (`NOTARY_WAIT_TIMEOUT`, default **25m**) and clearer failure output; the macOS release workflow sets a **90-minute** job timeout.
- **CI (macOS releases)**: Intel builds use **`macos-15-intel`** instead of the retired **`macos-13`** image (which no longer provisions runners); Apple Silicon builds use **`macos-15`**.

## [0.4.0] - 2026-04-18
### Changed
- When max width/height scaling is used (no crop), output filenames now include the scaled pixel dimensions (for example `myseq_1280x720.mp4` or `myseq_date_640x360.mp4`) together with the existing crop, overlay, and quality suffixes.

## [0.3.0] - 2026-03-01
### Added
- **New Scaling Options**: Added max width and max height parameters for proportional scaling
  - Available in both GUI and CLI when no crop mode is selected
  - Supports setting width only, height only, or both (fits within bounds)
  - Automatically ensures even dimensions for codec compatibility
  - Works with all overlay types (date, frame)
- **Enhanced GUI**: 
  - Added max width and max height input fields
  - Fields are automatically enabled/disabled based on crop selection
  - Increased window height to accommodate new controls
  - "None" is now the default crop selection
- **Improved Error Handling**: Fixed GUI error handling for better user experience

### Fixed
- GUI error handling now properly displays error messages
- CLI validation now properly enforces scaling/crop mode conflicts

## [0.2.2] - 2025-05-23
### Fixed
- Output video is now always the correct size (HD 1920x1080 or UHD 3840x2160) for all crop and overlay options
- Cropping now correctly respects 'keep_top' and 'keep_bottom' for HD and UHD
- Improved sequential image sequence detection (robust to prefix, zero-padding, and starting number)
- Dot-files and hidden files are always ignored
- GUI and CLI now both alert if images are not sequentially named

## [0.2.1] 
### Added
- GUI window now displays progress bar and percent complete updates

### Changed
- Update GUI window layout and add icon

## [0.2.0] 
### Added
- First version of project packaged as a Mac OS app for release
- New folder preference functionality to remember the last-used input and output directories
- Added app icon and screenshot to README

### Changed
- Updated macOS installation instructions in the README 

## [0.1.0] 

### Added
- Initial release of Simple Image Sequence Renderer (SISR)
- Command-line interface for video rendering
- GUI interface using PyQt6
- Support for date and frame number overlays
- Multiple crop options (Instagram, HD, UHD)
- GIF output support
- Progress bar and status updates
- Automated tests

### Features
- Image sequence to video conversion
- EXIF date extraction and overlay
- Multiple output formats (MP4, MOV, GIF)
- Customizable frame rates
- Temporary file management
- Cross-platform support 