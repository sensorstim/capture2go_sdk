<!--
SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>

SPDX-License-Identifier: MIT

Types of changes

### Added (for new features)
### Changed (for changes in existing functionality)
### Deprecated (for soon-to-be removed features)
### Removed (for now removed features)
### Fixed (for any bug fixes)
### Security (in case of vulnerabilities)
-->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-04-02

### Fixed

- Set layout of ctypes structs explicitely to fix `_pack_ is not compatible with gcc-sysv layout` errors in Python 3.14.

## [1.0.0] - 2025-10-15

### Added

- `capture2go.loadBinaryFile` function.

### Fixed

- Avoid usage of Python 3.12 f-string features.

## [0.8.0] - 2025-09-05

### Added

- Initial release.

[unreleased]: https://github.com/sensorstim/capture2go_sdk/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/sensorstim/capture2go_sdk/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/sensorstim/capture2go_sdk/compare/v0.8.0...v1.0.0
[0.8.0]: https://github.com/sensorstim/capture2go_sdk/releases/tag/v0.8.0
