# siun

[![PyPI - Version](https://img.shields.io/pypi/v/siun.svg)](https://pypi.org/project/siun)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/siun.svg)](https://pypi.org/project/siun)

-----

**Table of Contents**

- [Usage](#usage)
- [Installation](#installation)
- [Configuration](#configuration)
- [License](#license)
- [Name](#name)

## Usage

The most basic way to use `siun` is to simply run the `check` command:

```bash
siun check
```


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


### Install dev env

```bash
pip install -e .[dev]
```


## Configuration

Configuration happens through a toml file.

The default configuration looks like this:

```toml
# command which returns list of available updates
cmd_available = "pacman -Quq; if [ $? == 1 ]; then :; fi"  # pacman returns exit code 1 if there are no updates
# weight required to consider updates to be of available, warning, or critical level
thresholds = { available = 1, warning = 2, critical = 3 }
# minimum age of cached update state before it will be refreshed
cache_min_age_minutes = 30
# Custom output format - use with `--output-format=custom`
custom_format = "$status_text: $available_updates"

[criteria]
# setting for `critical` criterion
critical_pattern = "^archlinux-keyring$|^linux$|^pacman.*$"
# weight the criterion contributes to urgency score
critical_weight = 1
# setting for `count` criterion
count_threshold = 10
# setting weight to 0 disables check
count_weight = 0
# setting for `last_pacman_update` criterion
last_pacman_update_age_hours = 618  # 7 days
last_pacman_update_weight = 1
```


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
