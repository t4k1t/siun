# siun

[![PyPI - Version](https://img.shields.io/pypi/v/siun.svg)](https://pypi.org/project/siun)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/siun.svg)](https://pypi.org/project/siun)
[![codecov](https://codecov.io/gh/t4k1t/siun/graph/badge.svg?token=Y5D4KX42LL)](https://codecov.io/gh/t4k1t/siun)

<img height="128" alt="siun Icon" src="assets/icon/siun-icon.png" align="left">

Prioritize package updates that matter.

By calculating an urgency score, `siun` aims to help sysadmins decide how important available updates really are and why. It supports various built-in criteria and allows users to implement their own criteria in Python.

-----

[Usage](#usage) • [Installation](#installation) • [Configuration](#configuration) • [License](#license) • [Name](#name)

## Usage

On Arch Linux, or any other system that uses `pacman`, the most basic way to use `siun` is to simply run the `check` command:

```bash
siun check
```

Any other OS/distribution will require some [Configuration](#configuration) first.

### Check Command

The `check` command runs a configurable console command to find which packages can be updated and checks them against various criteria to determine how urgent it is to apply those updates.

#### Options

The `check` command supports a few options:
- `--quiet`: Suppress regular output; Useful if you only want to update the cache file
- `--no-update`: Don't refresh available updates, only read from cache if available
- `--no-cache`: Don't read or write cache file
- `--output-format`: Pick output format for urgency report; Available formats are `[plain|fancy|json|custom]`

### News Command

*NOTE:* Using the `news` command requires the `news` optional feature. See [Optional Features](#optional-features)

Running the `news` command prints out unread entries of any configured RSS or Atom feeds. See [Configuration](#configuration) for information on how to set up feed sources.

## Installation

```bash
pip install siun
```

### Optional Features

Some features require additional dependencies to work which will not be installed by default.

For example, in order to use the `notification` feature, install `siun` with the `notification` classifier:

```bash
pip install siun[notification]
```

The `notification` feature shows a desktop notification the first time a configurable threshold is exceeded. All variables available for the custom output format can also be used to customize the notification body and title.

*NOTE:* Using the `notification` feature in conjunction with the `--no-cache` flag will cause the notification to show up on every check, provided the requirements are met.

The `news` feature adds the `news` command. See above for more information on its usage.

### Development

```bash
# Set up dev env
uv sync --all-extras
```

## Configuration

Configuration happens through a TOML file. By default, `siun` will try to read the following files in order:

1. `$XDG_CONFIG_HOME/siun/config.toml`
2. `$HOME/.config/siun/config.toml`

See [examples/config.toml](examples/config.toml) for an example config. This example config also contains the default values which will be used if `siun` can't find any usable configuration.

## Migrating Configuration: v1.x to v2.0+

**Important:** Starting with `siun` version **2.0**, the configuration format has changed.  
If you are upgrading from any version **≤ 1.5.1**, you must update your config file to avoid errors.

### Why the Change?

The new format introduces multiple new configuration fields for better flexibility and future-proofing. E.g. the new `update_providers` field allows setting up multiple sources for package updates instead of only one.

### What Changed?

- **Old fields:**  
  1. `thresholds` → replaced by `v2_thresholds`
  2. `criteria` → replaced by `v2_criteria`
  3. `cmd_available` → replaced by `update_providers`
- **New fields:**  
  1. `v2_thresholds`: List of threshold objects with `name`, `score`, `color`, and `text`.
  2. `v2_criteria`: List of criterion objects with `name`, `weight`, and optional parameters.
  3. `update_providers`: Object describing how to get list of available updates.
     Update providers make it simpler than ever to set up `siun`. Instead of having to supply the command yourself, just pick an existing provider that does the work for you. E.g. the `pacman` update provider already knows how to get the list of available updates from `pacman` - no additional configuration required.

### Migration Steps

1. **Back up your old config:**  
   Copy your existing `config.toml` to a safe location.

2. **Replace old fields:**  
   Remove any `thresholds`, `criteria`, and `cmd_available` entries.

3. **Add new fields:**  
   Use the following template:

   ```toml
   # Thresholds
   [[v2_thresholds]]
   name = "critical"
   score = 3
   color = "red"
   text = "Updates required"

   [[v2_thresholds]]
   name = "warning"
   score = 2
   color = "yellow"
   text = "Updates recommended"

   [[v2_thresholds]]
   name = "available"
   score = 1
   color = "green"
   text = "Updates available"

   # Criteria
   [[v2_criteria]]
   name = "available"
   weight = 1

   [[v2_criteria]]
   name = "pattern"
   weight = 1
   pattern = "^archlinux-keyring$|^linux$|^pacman.*$"

   [[v2_criteria]]
   name = "count"
   weight = 1
   count = 15

   # Update provider
   [[update_providers]]
   name = "generic"
   cmd = ["checkupdates", "--nocolor"]
      ```

4. **Review other config options:**  
   Ensure any custom settings (e.g., `custom_format`, `notification`) are still valid.

5. **Test your setup:**  
   Run `siun check` and verify there are no configuration errors.

### Update Providers

Update providers tell `siun` how to fetch the list of packages with available updates. This is configured using the `[[update_providers]]` section in your `config.toml`.

> ℹ️ If you can't find a provider for your package manager of choice, you can always try to set up the `generic` provider instead.

#### Default Provider: pacman

By default, `siun` is configured to use the `pacman` update provider. This provider automatically runs `pacman -Qu` and parses its output, so no extra configuration is needed for most Arch Linux systems. If you use Arch or a compatible distribution, you can simply install and run `siun` without changing the provider.

Example default configuration:
```toml
[[update_providers]]
name = "pacman"
```

#### Custom Provider: generic

If you use a different package manager, or want to customize how updates are detected, you can use the `generic` provider. This lets you specify any shell command that outputs a list of updatable packages, one per line. The `generic` provider will treat each line as a package name.

Example configuration for the generic provider:
```toml
[[update_providers]]
name = "generic"
cmd = ["your-update-command", "--flag", "--another-flag"]
pattern = "(?P<name>.+)"
```
- `cmd`: List of command and arguments to run. Each line of output should be a package name.
- `pattern`: (Optional) Regex pattern to extract the package name. By default, it matches the whole line. The `generic` provider looks for the following match groups: `name`, `old_version`, `new_version`. The `name` group is required, all others are optional.

For example, to use the `checkupdates` script (from `pacman-contrib`), configure:
```toml
[[update_providers]]
name = "generic"
cmd = ["checkupdates", "--nocolor"]
pattern = "(?P<name>.+)"
```

If your update command outputs more details (like version numbers), you can adjust the `pattern` to extract those fields. See the [examples/config.toml](examples/config.toml) for more advanced patterns.

#### Choosing a Provider

- **Arch Linux users:** The `pacman` provider is recommended and enabled by default.
- **Other distributions:** Use the `generic` provider and set `cmd` to your update command.

After configuring, run `siun check` to verify your setup.

### Troubleshooting

- If you see errors about missing fields or invalid configuration, double-check the migration steps.
- See [examples/config.toml](examples/config.toml) for a complete, working example.

---

*NOTE: If your config is not updated, `siun` 2.0+ will fail to start or revert to defaults.*

### Automatically Run `siun check`

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

#### Systemd Unit & Timer

Since the default configuration gets the list of available package updates from `pacman` without syncing, it might be useful to define a system unit & timer which automatically updates the local `pacman` database. Find `pacman-sync.service` and `pacman-sync.timer` in [examples/systemd](examples/systemd) for examples of such.

*NOTE: When using the pacman-sync unit it might be tempting to not sync the pacman database on updating packages since the service will sync every day anyway. However, this is a bad idea. See the [Arch Linux Wiki](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported) for more information on this. A safer way to make sure package update information is up to date is to use the [`checkupdates`](#checkupdates) script*

### Automatically Clear Cache

In order to automatically clear `siun`'s cache when packages get updated, it's possible to set up a pacman hook. Simply edit the `siun-clear-cache.hook` file in the [examples/pacman](examples/pacman) folder to contain the correct `$HOME` path and copy it to `/etc/pacman.d/hooks/`. The example deletes the state cache after `Install`, `Upgrade`, and `Remove` operations.


## Criteria

`siun` checks a configurable list of criteria to determine how urgent updates are. Each criterion is defined in the `[[v2_criteria]]` section of your config file, specifying its type (`name`), parameters, and a `weight` that contributes to the total urgency `score`. The combined score from all matched criteria is then compared against your configured thresholds to determine the update status.

Setting the `weight` of a criterion to `0` will disable it. Disabled criteria do not get executed.

> ℹ️ Criteria can also be configured with a negative weight. As you might've alreay guessed, negative weigths will get subtracted from the urgency score.

### Built-in Criteria

The following criteria are built-in:
- `available`: Any updates are available
- `count`: Number of available updates exceeds threshold
- `pattern`: Any of the available updates is considered an important package based on the configured regex pattern

### Custom Criteria

You can also define your own criteria as Python code. Any python file in `$XDG_CONFIG_DIR/siun/criteria` will be checked for a class called `SiunCriterion` and run its `is_fulfilled` method.

> ❗ Custom criteria are loaded and executed as Python code from your local configuration directory. This means that any code placed in `$XDG_CONFIG_DIR/siun/criteria` will be executed with the same privileges as `siun`. Malicious or unsafe code in this directory could compromise your system. Only use custom criteria from trusted sources and review their contents before use.

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

#### Security Mitigations

To reduce risks, `siun` implements several safeguards in its code:

- **Explicit Loading:** Only `.py` files whose names match enabled criteria in your configuration are loaded.
- **Class Verification:** Each file must define a `SiunCriterion` class with an `is_fulfilled` method. Files missing this class or method are ignored.
- **Error Handling:** If a criterion fails to load or execute, a clear error is raised and reported, preventing silent failures.
- **No Remote Execution:** Criteria are only loaded from your local configuration directory; there is no remote code fetching.
- **Permission Checks:** Custom criteria don't get loaded from any world-writable directories.

Despite these measures, custom criteria are inherently powerful and can run arbitrary code. Always audit custom criteria before use.

### Custom Output Format

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
