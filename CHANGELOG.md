# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added

- Expanded CLI with organise/undo commands.
- New multi-view GUI using `QStackedWidget` with separate view classes
- Background threading support for async operations
- Modular dialog system
- Drag-and-drop folder selection support
- SVG utility functions for dynamic icon rendering
- UI constants module for centralised configuration
- `typer-extensions` for extended CLI command functionality
- Proper package structure for UI modules with exports
- Mock DB path fixture for tests.
- Type checking with 'ty' type checker

### Changed

- Main window refactored from container-based to stacked widget
- CLI migration from standard `typer` to `typer-extensions`
- Improved scan command output and return value.
- Restructured Rust module for better maintainability.
- Enhanced CLI output formatting with improved spacing & markup.
- Improved code formatting consistency across Python & Rust files.
- Replaced `pre-commit` with `prek` for faster pre-commit execution
- Upgraded pre-commit hooks configuration & naming
- Standardised naming convention: photo_files → image_files across all modules
- Dependency upgrades: rusqlite->0.38, maturin->1.11.5, ruff->0.14.11, and ty->0.0.12
- Replace `Makefile` with `Justfile` for simpler task management

### Fixed

- Removed large DB file and cleaned up Rust package structure.
- Updated metadata tests.


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
