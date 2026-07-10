% siun(1) | General Commands Manual
% Thomas Kager
% January 2026

# NAME

**siun** - Prioritize package updates that matter.

# SYNOPSIS

**siun** [OPTIONS]

# DESCRIPTION

By calculating an urgency score, _siun_ aims to help sysadmins decide how important available updates really are and why. It supports various built-in criteria and allows users to implement their own criteria in Python.

# OPTIONS

**-h**, **\--help**
: Print help information.

**\--version**
: Print version information.

# COMMANDS

**check(1)**
: Fetch list of available updates (unless chached) and report on urgency.

**news(1)**
: Print latest unread (package) news.

# CONFIGURATION FILE

_siun_ reads its configuration from a file in one of the following locations (checked in order):

1. _$XDG_CONFIG_HOME/siun/config.toml_
2. _$HOME/.config/siun/config.toml_
3. _/.config/siun/config.toml_ (if HOME is not set)

_siun_ tries to auto-detect suitable update providers from distro metadata (**ID** and **ID_LIKE** in _/etc/os-release_, with fallback to _/etc/system-release_). If no providers can be guessed, configure at least one **[[update_providers]]** entry manually. See _siun_(5) for details on configuration options.

# BUGS

Issue reports or feature requests can be filed at https://github.com/t4k1t/siun/issues
