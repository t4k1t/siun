# siun

[![PyPI - Version](https://img.shields.io/pypi/v/siun.svg)](https://pypi.org/project/siun)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/siun.svg)](https://pypi.org/project/siun)
[![codecov](https://codecov.io/gh/t4k1t/siun/graph/badge.svg?token=Y5D4KX42LL)](https://codecov.io/gh/t4k1t/siun)

<img height="128" alt="siun Icon" src="assets/icon/siun-icon.png" align="left">

Check how urgently packages have to be upgraded.

`siun` will check available updates for various criteria - like the number of updates, or important package names. Each criterion will count towards a total score which gives an indication of how urgently upgrades are required. You can also write your own criteria using Python.

-----

**Table of Contents**

- [Usage](#usage)
- [Installation](#installation)
- [Configuration](#configuration)
- [License](#license)
- [Name](#name)

## Usage

On Arch Linux, or any other system that uses `pacman`, the most basic way to use `siun` is to simply run the `check` command:

```bash
siun check
```

Any other OS/distribution will require some [configuration](#configuration) first.

### Check command

The `check` command runs a configurable console command to find which packages can be updated and checks them against various criteria to determine how urgent it is to apply those updates.

#### Options

The `check` command supports a few options:
- `--quiet`: Suppress regular output; Useful if you only want to update the cache file
- `--no-update`: Don't refresh available updates, only read from cache if available
- `--no-cache`: Don't read or write cache file
- `--output-format`: Pick output format for urgency report; Available formats are `[plain|fancy|json|i3status|custom]`

## Installation

```bash
pip install siun
```

### Optional features

Some features require additional dependencies to work which will not be installed by default.

Currently, this only applies to the `notification` feature. In order to use this feature, install `siun` with the `notification` classifier:

```bash
pip install siun[notification]
```

The `notification` feature shows a desktop notification the first time a configurable threshold is exceeded. All variables available for the custom output format can also be used to customize the notification body and title.

*NOTE:* Using the `notification` feature in conjunction with the `--no-cache` flag will cause the notification to show up on every check, provided the requirements are met.

### Development

```bash
# Set up dev env
uv sync
```

## Configuration

Configuration happens through a TOML file.

The default configuration looks like this:

```toml
# Command which returns list of available updates
cmd_available = "pacman -Quq; if [ $? == 1 ]; then :; fi"  # pacman returns exit code 1 if there are no updates
# Weight required to consider updates to be of `available`, `warning`, or `critical` level
thresholds = { available = 1, warning = 2, critical = 3 }
# Minimum age of cached update state before it will be refreshed
cache_min_age_minutes = 30
# Custom output format - use with `--output-format=custom`
custom_format = "$status_text: $available_updates"
# State file location
state_file = "/tmp/siun-state.json"
# Notification configuration

[criteria]
# Setting for `critical` criterion
critical_pattern = "^archlinux-keyring$|^linux$|^pacman.*$"
# Weight the criterion contributes to urgency score
critical_weight = 1
# Setting for `count` criterion
count_threshold = 10
# Setting weight to 0 disables check
count_weight = 0
# Setting for `last_pacman_update` criterion
last_pacman_update_age_hours = 618  # 7 days
last_pacman_update_weight = 1

[notification]
# Notification body, supports format placeholders
message = "$available_updates"
# Notification title, supports format placeholders
title = "$status_text"
# Notification urgency ["low"|"normal"|"critical"]
urgency = "normal"
# Notification timeout, `0` means no timeout
timeout = 10000
# Notification icon, can be either icon name or path
icon = "siun-icon"
# Minimum threshold for notification to show ["available"|"warning"|"critical"]
threshold = "available"
```

### Automatically run `siun check`

It is recommended to set up some kind of automation for running `siun`. One possibility is to set up a `systemd` user unit & timer. Find `siun.service` and `siun.timer` in [examples/systemd](examples/systemd) for examples of such.

Since `siun` is supposed be able to run on most Arch Linux installations, it only calls `pacman` to check for package updates by default. This has the obvious drawback that it will only show updates if the local `pacman` database has been synced recently. There are multiple options to solve this:

#### checkupdates

The first, and recommended, option is to use the `checkupdates` script. It is available in the `pacman-contrib` package. Once it's installed, simply update the configuration like so:

```toml
cmd_available = "checkupdates --nocolor | cut -d ' ' -f1"
```

*NOTE: The pipe to `cut` can be removed to also get a diff of version numbers - but for basic operation this is not required*

#### systemd unit & timer

Since the default configuration gets the list of available package updates from `pacman` without syncing, it might be useful to define a system unit & timer which automatically updates the local `pacman` database. Find `pacman-sync.service` and `pacman-sync.timer` in [examples/systemd](examples/systemd) for examples of such.

*NOTE: When using the pacman-sync unit it might be tempting to not sync the pacman database on updating packages since the service will sync every day anyway. However, this is a bad idea. See the [Arch Linux Wiki](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported) for more information on this. A safer way to make sure package update information is up to date is to use the [`checkupdates`](#checkupdates) script*

### Automatically clear cache

In order to automatically clear `siun`'s cache when packages get updated, it's possible to set up a pacman hook. Simply edit the `siun-clear-cache.hook` file in the [examples/pacman](examples/pacman) folder to contain the correct `$HOME` path and copy it to `/etc/pacman.d/hooks/`. The example deletes the state cache after `Install`, `Upgrade`, and `Remove` operations.


## Criteria

`siun` checks various criteria to determine how urgent updates are. Each criterion has a `weight` which contributes to a total `score`. This `score` is then compared to a list of thresholds to determine wheter updates are `available`, `recommended` or `required`.

### Built-in criteria

The following criteria are built-in:
- `available`: Any updates are available
- `count`: Number of available updates exceeds threshold
- `critical`: Any of the available updates is considered a critical package
- `lastupdate`: Time since last update has exceeded threshold

### Custom criteria

You can also define your own criteria as Python code. Any python file in `$XDG_CONFIG_DIR/siun/criteria` will be checked for a class called `SiunCriterion` and run its `is_fulfilled` method.

Example custom criterion checking if any available updates are reported by `arch-audit`:

```python
import subprocess


class SiunCriterion:
    """Custom criterion."""

    def is_fulfilled(self, criteria_settings: dict, available_updates: list):
        """Check if any available updates are in arch-audit list."""
        audit_packages = []
        arch_audit_run = subprocess.run(
            ["/usr/bin/arch-audit", "-q", "-u"],
            check=True,
            capture_output=True,
            text=True,
        )
        audit_packages = arch_audit_run.stdout.splitlines()

        return bool(set(available_updates) & set(audit_packages))
```

### Custom output format

It's possible to define your own output format by setting a `custom_format` in the configuration file, and passing `--output-format=custom` to the `siun check` call. See [Configuration](#configuration).

Available format variables:

- `$available_updates`:      Comma-separated list of available updates
- `$last_update`:            Date and time of last time siun checked for updates in ISO format
- `$matched_criteria`:       Comma-separated names of matched criteria
- `$matched_criteria_short`: Comma-separated matched criteria, shortened to 2 characters
- `$score`:                  Sum weight of matched criteria
- `$status_text`:            Text representation of update status, e.g. "Updates available"
- `$update_count`:           Number of available updates

## License

`siun` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Name

`siun` stands for, and tries to answer, the question "Should I upgrade now?".
