# Changelog

## [1.0.1] - 2026-07-14

### Added

- Empty state overlay on the controller view when no controllers are shown
- Preset builder support for controllers without an assigned part

### Changed

- Improved preset dialog UX and parent name synchronization
- Override presets replace base `muted` / `muted_patterns`
- Preset builder always writes an explicit mute state for parts

### Fixed

- Preset dialog name sync with parent window components
- Pair mode column refresh after related UI updates

## [1.0.0] - 2026-05

### Added

- Initial release of defQA for Maya
- Generate and delete check animation from a controller set
- YAML preset / override system for part classification and test values
- GUI for scanning controllers, editing settings, and managing presets
- Vendored PyYAML and Qt.py for environments without pip packages

[1.0.1]: https://github.com/zebraed/defQA/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/zebraed/defQA/releases/tag/v1.0.0
