# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Database build pipeline ported to Rust, replacing Python-side scoring and filtering.
- Unit tests for export.rs, scoring.rs, and wikidata.rs build pipeline modules.
- Streaming and parsing the Wikidata JSON dump to extract GeoNames IDs and sitelink counts.
- Typed Serde structs for safer field access.
- Downloading and parsing monthly bz2 pageview dumps per place.
- Reusable String buffer via read_line to reduce per-line allocations.
- Weighted importance scoring using pageviews & sitelink count, normalised to the 99th percentile.
- Build DB export step with regional pruning cap and optimised indexes for the app DB.
- geonames_id column and intermediate score columns in the build schema.
- CustomRotatingFileHandler in logger.py that closes and reopens the stream after rollover.
- LOG_DIR constant centralised under APP_DATA_DIR in paths.py.
- CMake setup step in CI workflow.
- Progress callback support in organise_photos.
- Expanded CLI with organise/undo commands.
- New multi-view GUI using `QStackedWidget` with separate view classes.
- Background threading support for async operations.
- Modular dialog system.
- Drag-and-drop folder selection support.
- Subfolder inclusion checkbox in SetupView.
- SVG utility functions for dynamic icon rendering.
- UI constants module for centralised configuration.
- `typer-extensions` for extended CLI command functionality.
- Proper package structure for UI modules with exports.
- Mock DB path fixture for tests.
- Type checking with 'ty' type checker.

### Changed

- OrganiserThread now calls the real function instead of a simulated loop.
- scoring.rs renamed to geo_scoring.rs to distinguish geocoding scoring from build-time importance scoring.
- build_rust.py now builds with --features build-db.
- Removed hardcoded importance scores and keyword filters from constants.py.
- Build and app DBs now use separate paths, build DB retains full data, app DB is pruned at export.
- Main window refactored from container-based to stacked widget.
- CLI migration from standard `typer` to `typer-extensions`.
- Improved scan command output and return value.
- Restructured Rust module for better maintainability.
- Enhanced CLI output formatting with improved spacing & markup.
- Improved code formatting consistency across Python & Rust files.
- Explicit keyword arguments across all function calls for clarity and type-hinting.
- Inline variable type annontations across codebase.
- Replaced `pre-commit` with `prek` for faster pre-commit execution.
- Upgraded pre-commit hooks configuration & naming.
- Standardised naming convention: photo_files → image_files across all modules.
- Replaced `Makefile` with `Justfile` for simpler task management.
- CI Linux step expanded to install build-essential and pkg-config for zlib-ng-compat build support.
- Dependency upgrades:
  - chrono->0.4.44
  - icecream->2.2.0
  - maturin->1.13.3
  - prek->0.4.2
  - pygments->2.20.0
  - pyo3->0.28.3
  - pyside->6.11.0
  - pytest->9.0.3
  - pytest-cov->7.1.0
  - ruff->0.15.14
  - rusqlite->0.40
  - rust-just->1.51.0
  - ty->0.0.39

### Fixed

- Removed large DB file and cleaned up Rust package structure.
- Updated metadata tests.
- Removed hardcoded Qt plugin path detection workaround - no longer needed with PySide 6.11.
- GPS coordinate degree validation widened from 90° to 180° to correctly handle longitude.
- State file saves are now atomic using a .tmp + os.replace() pattern.

## [0.2.0] - 2026-01-05

### Added

- Scan, organise and undo commands to the CLI.
- Major expansion of the UI, including new panels, widgets, and improved user experience.
- Rust module restructuring and integration for performance and maintainability.
- Undo functionality and state management for photo organisation.
- Enhanced logging with rotation and environment configuration.
- New and improved tests, including integration and unit tests.

### Changed

- Refactored core modules and UI code for better modularity and maintainability.
- Improved scan command output and performance metrics.
- Updated project structure for Rust and Python components.

### Fixed

- Various bug fixes and test improvements.

## [0.1.0] - 2025-11-17

### Added

- Initial release of Photidy.
- Core photo organisation and metadata extraction functionality.
- Basic CLI and UI for photo management.
- Rust backend integration for metadata processing.
- Logging, error handling, and configuration utilities.
- Initial test suite for core modules.

[unreleased](https://github.com/rdawebb/Photidy/compare/v0.2.0-alpha...main)
[0.2.0](https://github.com/rdawebb/Photidy/compare/v0.1.0-alpha...v0.2.0-alpha)
[0.1.0](https://github.com/rdawebb/Photidy/releases/tag/v0.1.0-alpha)
