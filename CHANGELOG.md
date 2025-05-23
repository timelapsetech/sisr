# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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