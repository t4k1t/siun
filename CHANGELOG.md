# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-10-19

### Added

- More consistent error handling and reporting
- `--no-cache` option for `check` command
- `--no-update` option for `check` command
- `--quiet` option for `check` command
- Criterion for time of last update
- Additional unit tests
- Initial support for custom user criteria
- Config validation
- `unkown` state when there is no persisted state on disk

### Changed

- Update example config
- Update score on the fly
- Separate update query from persisting state
- Merge `get-state` and `write-state` subcommands into `check` subcommand
- Switch from `hatch` to `rye`

### Fixed

- Typo in default config
- Make sure state file always contains valid JSON
- Minimum python version

## [0.2.0] - Unreleased

### Added

- Initial PoC
- Support for config file

### Changed

- Rename project

### Removed

- Badges pointing to existing tool
