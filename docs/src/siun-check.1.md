% siun-check(1) | Siun Manual
% Thomas Kager
% January 2026

# NAME

siun-check - Fetch list of available updates (unless chached) and report on urgency.

# SYNOPSIS

**siun** check [OPTIONS]

# DESCRIPTION

Fetch list of available updates, apply configured criteria and print calculated urgency score. See _siun_(5) for criteria configuration.

# OPTIONS

**-h**, **\--help**
: Print help information.

**-C**, **\--config-path**
: Override config file location. See _siun_(5) for details on configuration options.

**-o**, **\--output-format** [ plain | fancy | json | custom ]
: Pick format for update check.

**--cache** / **-n**, **\--no-cache**
: Ignore existing state on disk. Defaults to **cache**.

**-U**, **\--no-update**
: Don't fetch available updates, only check.

**-q**, **\--quiet**
: Suppress output.

# BUGS

Issue reports or feature requests can be filed at https://github.com/t4k1t/siun/issues
