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
- `--output-format`: Pick output format for urgency report; Available formats are `[plain|fancy|json|custom]`

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

Configuration happens through a TOML file. By default, `siun` will try to read the following files in order:

1. `$XDG_CONFIG_HOME/siun/config.toml`
2. `$HOME/.config/siun/config.toml`

See [examples/config.toml](examples/config.toml) for an example config. This example config also contains the default values which will be used if `siun` can't find any usable configuration.

## Migrating Configuration: v1.x to v2.0+

**Important:** Starting with `siun` version **2.0**, the configuration format has changed.  
If you are upgrading from any version **≤ 1.5.1**, you must update your config file to avoid errors.

### Why the change?

The new format introduces `v2_thresholds` and `v2_criteria` for better flexibility and future-proofing.  
Old fields (`thresholds`, `criteria`) are no longer supported.

### What changed?

- **Old fields:**  
  - `thresholds` → replaced by `v2_thresholds` (list of objects)
  - `criteria` → replaced by `v2_criteria` (list of objects)
- **New fields:**  
  - `v2_thresholds`: List of threshold objects with `name`, `score`, `color`, and `text`
  - `v2_criteria`: List of criterion objects with `name`, `weight`, and optional parameters
  - 
### Migration steps

1. **Backup your old config:**  
   Copy your existing `config.toml` to a safe location.

2. **Replace old fields:**  
   Remove any `thresholds` and `criteria` entries.

3. **Add new fields:**  
   Use the following template:

   ```toml
   v2_thresholds = [
     { name = "critical", score = 3, color = "red", text = "Updates required" },
     { name = "warning", score = 2, color = "yellow", text = "Updates recommended" },
     { name = "available", score = 1, color = "green", text = "Updates available" }
   ]

   v2_criteria = [
     { name = "available", weight = 1 },
     { name = "pattern", weight = 1, pattern = "^archlinux-keyring$|^linux$|^pacman.*$" },
     { name = "count", weight = 1, count = 15 }
   ]
   ```

4. **Review other config options:**  
   Ensure any custom settings (e.g., `cmd_available`, `custom_format`, `notification`) are still valid.

1. **Test your setup:**  
   Run `siun check` and verify there are no configuration errors.
2. 
### Troubleshooting

- If you see errors about missing fields or invalid configuration, double-check the migration steps.
- See [examples/config.toml](examples/config.toml) for a complete, working example.

---

**Note:** If your config is not updated, `siun` 2.0+ will fail to start or revert to defaults.

### Automatically run `siun check`

It is recommended to set up some kind of automation for running `siun`. One possibility is to set up a `systemd` user unit & timer. Find `siun.service` and `siun.timer` in [examples/systemd](examples/systemd) for examples of such.

Since `siun` is supposed be able to run on most Arch Linux installations, it only calls `pacman` to check for package updates by default. This has the obvious drawback that it will only show updates if the local `pacman` database has been synced recently. There are multiple options to solve this:

#### checkupdates

The first, and recommended, option is to use the `checkupdates` script. It is available in the `pacman-contrib` package. Once it's installed, simply update the configuration like so:

```toml
cmd_available = "checkupdates --nocolor | cut -d ' ' -f1"
```

*NOTE: The pipe to `cut` can be removed to also get a diff of version numbers - but for basic operation this is not required*

`checkupdates` can be combined with [`aur-check-updates`](https://aur.archlinux.org/packages/aur-check-updates) in order to also take AUR packages into account:

```toml
cmd_available = "{ checkupdates --nocolor; aur-check-updates -n --raw; } | cut -d ' ' -f1"
```

#### systemd unit & timer

Since the default configuration gets the list of available package updates from `pacman` without syncing, it might be useful to define a system unit & timer which automatically updates the local `pacman` database. Find `pacman-sync.service` and `pacman-sync.timer` in [examples/systemd](examples/systemd) for examples of such.

*NOTE: When using the pacman-sync unit it might be tempting to not sync the pacman database on updating packages since the service will sync every day anyway. However, this is a bad idea. See the [Arch Linux Wiki](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported) for more information on this. A safer way to make sure package update information is up to date is to use the [`checkupdates`](#checkupdates) script*

### Automatically clear cache

In order to automatically clear `siun`'s cache when packages get updated, it's possible to set up a pacman hook. Simply edit the `siun-clear-cache.hook` file in the [examples/pacman](examples/pacman) folder to contain the correct `$HOME` path and copy it to `/etc/pacman.d/hooks/`. The example deletes the state cache after `Install`, `Upgrade`, and `Remove` operations.


## Criteria

`siun` checks a configurable list of criteria to determine how urgent updates are. Each criterion is defined in the `[[v2_criteria]]` section of your config file, specifying its type (`name`), parameters, and a `weight` that contributes to the total urgency `score`. The combined score from all matched criteria is then compared against your configured thresholds to determine the update status.

### Built-in criteria

The following criteria are built-in:
- `available`: Any updates are available
- `count`: Number of available updates exceeds threshold
- `pattern`: Any of the available updates is considered an important package based on the configured regex pattern
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
