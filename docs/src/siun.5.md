% siun(5) | File Formats Manual
% Thomas Kager
% January 2026

# NAME

siun - **siun** configuration file

# DESCRIPTION

_siun_(1) obtains configuration data from the following sources in the following order:

1. _$XDG_CONFIG_HOME/siun/config.toml_
2. _$HOME/.config/siun/config.toml_
3. _/.config/siun/config.toml_ - if HOME is not set

# GENERAL SETTINGS

**cache_age_minutes**
: Minimum age of cached update state before it will be refreshed.

**custom_format**

: Custom output format - use with **\--output-format=custom**. Available variables for **custom_format**:

    **$available_updates**: Comma-separated list of available updates.

    **$last_update**: Date and time of last time siun checked for updates in ISO format.

    **$matched_criteria**: Comma-separated names of matched criteria.

    **$matched_criteria_short**: Comma-separated matched criteria, shortened to 2 characters.

    **$score**: Sum weight of matched criteria.

    **$status_text**: Text representation of update status, e.g. "Updates available".

    **$update_count**: Number of available updates.

**state_dir**
: State file location.

# UPDATE-PROVIDER

Only relevant for _siun-check_(1).

Configure source of available updates. Each provider has at least a **name** by which it can be identified, but may have additional settings.

**pacman**
: Default update provider for Arch Linux based distributions. Uses _pacman_(8) to fetch list of available updates.
No additional settings.

**generic**

: Generic update provider. Runs a provided shell command to fetch list of available updates. Expects output to be one line per update.
Additional settings:

    **cmd**: Shell command to fetch available updates. Output is expected to be one line per update. **Required**.

    **pattern**: Python regular expression to extract update information from **cmd**  output. Uses named groups to designate the following attributes: name, old_version, new_version. Only the name group is required. For example, here is a simple pattern matching updates with only characters in the name and numbers and dots in the version strings:

       ```^(?P<name>[a-z]+)\s+(?P<old_version>[\.0-9]+)\s+\-\>\s+(?P<new_version>[\.0-9\+]+)$``` 

# V2-CRITERIA

Only relevant for _siun-check_(1).

All criteria have a **name** and a **weight**. The **name** is used to pick the criterion. The **weight** is the value added to the urgency score if the criterion matches. Criteria may support and even require additional settings.

**available**
: Matches if any updates are available. No additional settings.

**count**
: Matches if number of available updates exceeds threshold. Additional settings:

    **count**: Count threshold.

**pattern**
: Matches if any of the available updates matches the configured regex pattern. Additional settings:

    **pattern**: Regex pattern to match available updates to.

In addition to the criteria provided by _siun_(1), users can define their own criteria. Any python file in `$XDG_CONFIG_DIR/siun/criteria` will be checked for a class called `SiunCriterion` with a `is_fulfilled` method. Custom criteria will only be loaded and executed if they have been configured.

Example custom criterion checking if any available updates are reported by `arch-audit`:

    python
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

# V2-THRESHOLDS

Only relevant for _siun-check_(1).

The urgency score itself is not very useful since it's just a number. In order to get a little more out of it, thresholds can be configured. Thresholds allow to add more information to given scores (e.g. a color for formatting or a name). A threshold is activated once the calculated urgency exceeds the threhold's **score**.

**name**
: Unique name.

**score**
: Minimum sum of criteria weights to consider this threshold exceeded. Integer.

**color**
: Color for output customization. Optional.

**text**
: Text for output customization.

# NOTIFICATION

Only relevant for _siun-check_(1).

The **notification** section makes it easy to configure desktop notifications once certain urgency score thresholds have been exceeded. It can be omitted entirely if showing a notification is not desired.

Notifications are only shown for the first time a threshold is exceeded. Once the urgency score drops again or is cleared, notifications will be reset and can be shown again.

**message**
: Notification body, supports the same format placeholders as the **custom_format** setting.

**title**
: Notification title, supports the same format placeholders as the **custom_format** setting.

**urgency**
: Notification urgency [ **"low"** | **"normal"** | **"critical"** ].

**timeout**
: Notification timeout, **0** means no timeout.

**icon**
: Notification icon, can be either an icon name or a path.

**threshold**
: Minimum threshold for notification to show. Maps to **name** values of **v2_thresholds** settings.

The following example sets up a desktop notification containing the text of the current urgency threshold - but only if the score exceeds the threshold called "warning":

  ```toml
  [notification]
  title = "$status_text"
  threshold = "warning"
  ```


# MINIMAL CONFIGURATION

A minimal config file might look something like this:

  ```toml
  [[v2_thresholds]]
  name = "critical"
  score = 3
  color = "yellow"
  text = "Updates required!"

  [[v2_thresholds]]
  name = "warning"
  score = 2
  color = "blue"
  text = "Updates recommended."

  [[v2_thresholds]]
  name = "available"
  score = 1
  color = "green"
  text = "Updates available."

  [[v2_criteria]]
  name = "pattern"
  weight = 2
  pattern = "^archlinux-keyring$|^linux$|^firefox$|^pacman.*$|^systemd$|^openssl$"

  [[v2_criteria]]
  name = "count"
  weight = 1
  count = 20
  ```
