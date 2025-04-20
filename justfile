alias cov := coverage
alias ta := testall

# run unit tests with coverage generation
@test:
    uv run coverage run -m pytest -m "not feature_notification"

# run unit tests, including optional features with coverage generation
@testall:
    uv run coverage run -m pytest

# generate coverage report
@coverage REPORT_TYPE='report':
    uv run coverage {{REPORT_TYPE}}

# clean dist
@clean:
    echo "Cleaning up existing artifacts…"
    rm -f dist/*.{tar.gz,whl}

# build dist
@build: clean
    echo "Building dist"
    uv build
