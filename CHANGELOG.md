# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Changed

- example config to be up to date
- score to update on the fly
- update query to be separate from persisting state
- `get-state` and `write-state` subcommands into one `check` subcommand
- project/package management from `hatch` to `rye`

### Fixed

- typo in default config
- state file to always contains valid JSON
- minimum python version

## [0.2.0] - Unreleased

### Added

- initial PoC
- support for config file

### Changed

- project name

### Removed

- badges pointing to existing tool
