% siun-news(1) | Siun Manual
% Thomas Kager
% January 2026

# NAME

siun-news - Print latest unread (package) news.

# SYNOPSIS

**siun** news [OPTIONS]

# DESCRIPTION

Print latest news from configurable RSS or Atom feeds. _siun-news_(1) remembers which news items have been seen already based on ETag and Last-Modified headers.

# OPTIONS

**-h**, **\--help**
: Print help information.

**-C**, **\--config-path**
: Override config file location. See _siun_(5) for details on configuration options.

**--nocolor**
: Do not colorize output.

# BUGS

Issue reports or feature requests can be filed at https://github.com/t4k1t/siun/issues
