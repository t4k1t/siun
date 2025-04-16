# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-04-16

### Added

- Python 3.13 as supported version
- `state_file` README config example
- More systemd unit & timer examples
- A logo for the project 🎉

### Changed

- Default `state_file` location
- Extended configuration section in README to cover more complete setup
- Switched to `uv`

### Fixed

- Missing GitHub version links in CHANGELOG

## [1.2.0] - 2025-01-12

### Added

- support for choosing state file path via config
- unit tests for custom output format

### Changed

- ruff linting settings to ignore some less helpful rules

### Fixed

- default value for thresholds setting
- various unit tests

## [1.1.0] - 2024-12-05

### Added

- support for custom output format
- classifiers and ruff configuration to `pyproject.toml`

### Changed

- handling of default config values to utilize `pydantic`
- changelog wording to be more consistent
- additional linting

## [1.0.0] - 2024-10-19

### Added

- more consistent error handling and reporting
- `--no-cache` option for `check` command
- `--no-update` option for `check` command
- `--quiet` option for `check` command
- criterion for time of last update
- additional unit tests
- initial support for custom user criteria
- config validation
- `unkown` state when there is no persisted state on disk
- initial PoC
- support for config file

### Changed

- example config to be up to date
- score to update on the fly
- update query to be separate from persisting state
- `get-state` and `write-state` subcommands into one `check` subcommand
- project/package management from `hatch` to `rye`
- project name

### Fixed

- typo in default config
- state file to always contains valid JSON
- minimum python version

### Removed

- badges pointing to existing tool

[unreleased]: https://github.com/t4k1t/siun/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/t4k1t/siun/compare/1.2.0...1.3.0
[1.2.0]: https://github.com/t4k1t/siun/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/t4k1t/siun/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/t4k1t/siun/releases/tag/v1.0.0
