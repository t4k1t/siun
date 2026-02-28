alias cov := coverage
alias ta := testall

# Run unit tests with coverage generation
@test:
    uv run coverage run -m pytest -m "not feature_notification and not feature_news"

# Run unit tests, including optional features with coverage generation
@testall:
    uv run coverage run -m pytest

# Generate coverage report
@coverage REPORT_TYPE='report':
    uv run coverage {{REPORT_TYPE}}

# Lint source
@lint:
    uv run --frozen ruff check src/
    uv run --frozen ty check src/

# Clean dist
@clean:
    echo "Cleaning up existing artifacts…"
    rm -f "dist/*.{tar.gz,whl}"

# Build dist
@build: clean
    echo "Building dist…"
    uv build

# Upgrade dependencies
@upgrade:
    echo "Upgrading dependencies…"
    uv lock --upgrade

# Preview and build man pages
@preview-man:
    pandoc docs/src/siun.1.md -s -t man | man -l -

@preview-man-5:
    pandoc docs/src/siun.5.md -s -t man | man -l -

@preview-man-check:
    pandoc docs/src/siun-check.1.md -s -t man | man -l -

@preview-man-news:
    pandoc docs/src/siun-news.1.md -s -t man | man -l -

@build-man:
    pandoc docs/src/siun.1.md -s -t man | gzip --stdout - > docs/man/siun.1.gz
    pandoc docs/src/siun-check.1.md -s -t man | gzip --stdout - > docs/man/siun-check.1.gz
    pandoc docs/src/siun-news.1.md -s -t man | gzip --stdout - > docs/man/siun-news.1.gz
    pandoc docs/src/siun.5.md -s -t man | gzip --stdout - > docs/man/siun.5.gz
