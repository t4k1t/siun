#!/bin/bash

set -e

RSH_PROJECT="siun"
RSH_REPO="https\:\/\/github\.com\/t4k1t\/$RSH_PROJECT"
RSH_PAGER="/usr/bin/bat"
rsh_skip=${RSH_SKIP}

# TODO: Check git branch
main() {
    # Check if there are any TODOs in the code - requires todo.sh
    check_todos

    # Calculate next release number
    {
        read -r latest_version
        read -r next_version
    } <<<$(get_version_info "$1")
    echo "New version is: $next_version"

    read -p "Continue to release version '$next_version'? (y/N)" confirmation
    case "$confirmation" in
    Y | y | Yes | yes) echo "Releasing $next_version…" ;;
    *) err "Cancelled" ;;
    esac

    # Update changelog
    if [[ ${rsh_skip,,} = *'changelog'* ]]; then
        echo "Skipping CHANGELOG…"
    else
        update_changelog "$latest_version" "$next_version"
    fi

    # Update version in pyproject.toml
    if [[ ${rsh_skip,,} = *'version'* ]]; then
        echo "Skipping version update…"
    else
        update_version "$latest_version" "$next_version"
    fi

    # Commit release changes
    if [[ ${rsh_skip,,} = *'commit'* ]]; then
        echo "Skipping commit…"
    else
        commit_changes "$latest_version" "$next_version"
    fi

    # Create release tag and push changes
    if [[ ${rsh_skip,,} = *'tag_and_push'* ]]; then
        echo "Skipping tag and push…"
    else
        tag_and_push "$latest_version" "$next_version"
    fi

    # Create release on GH, including release notes from changelog
    if [[ ${rsh_skip,,} = *'gh_release'* ]]; then
        echo "Skipping GH release…"
    else
        create_gh_release "$latest_version" "$next_version"
    fi

    # Build dist
    if [[ ${rsh_skip,,} = *'build'* ]]; then
        echo "Skipping build…"
    else
        # Clean up
        rm -f dist/*
        # Build
        uv build
    fi

    # Publish dist to PyPI
    if [[ ${rsh_skip,,} = *'publish'* ]]; then
        echo "Skipping publishing…"
    else
        uv publish
    fi

    # Clean up backup files
    if [[ ${rsh_skip,,} = *'cleanup'* ]]; then
        echo "Skipping cleanup…"
    else
        rm -f pyproject.toml.bak CHANGELOG.md.bak
    fi
}

err() {
    echo "$1" >&2
    exit 1
}

tag_and_push() {
    latest_version="$1"
    next_version="$2"
    read -p "Push tag and changes? (y/N)" confirmation
    case "$confirmation" in
    Y | y | Yes | yes) git tag -a "v$2" -m "$2 && "git push --follow-tags ;;
    *) echo "Cancelled push…" ;;
    esac
}

commit_changes() {
    latest_version="$1"
    next_version="$2"
    git add CHANGELOG.md pyproject.toml uv.lock
    read -p "Commit changes? (y/N)" confirmation
    case "$confirmation" in
    Y | y | Yes | yes) git commit -m "Release $next_version" ;;
    *) echo "Cancelled commit." ;;
    esac
}

create_gh_release() {
    latest_version="$1"
    next_version="$2"
    release_notes=$(sed -n "/^## \[$next_version\]/,/^## /p" CHANGELOG.md | sed '1d;$d')
    if [ -z "$release_notes" ]; then
        err "No changelog entries found for version $next_version."
    fi
    echo -e "Generated release notes:\n"
    echo -e "$release_notes\n"

    read -p "Publish release notes on GH? (y/N)" confirmation
    case "$confirmation" in
    Y | y | Yes | yes) gh release create "v$next_version" -t "v$next_version" --notes "$release_notes" || err "Failed to create GitHub release" ;;
    *) echo "Cancelled GH release." ;;
    esac
}

update_version() {
    latest_version="$1"
    next_version="$2"
    if [ -f "pyproject.toml" ]; then
        sed -i.bak "s/version = \"$latest_version\"/version = \"$next_version\"/" pyproject.toml
        uv sync --all-extras --dev
        echo "Updated pyproject.toml and uv.lock with new version: $next_version"
    else
        err "pyproject.toml not found!"
    fi
}

update_changelog() {
    latest_version="$1"
    next_version="$2"
    if [ -f "CHANGELOG.md" ]; then
        # Create .bak file, then replace the current Unreleased version and update corresponding GH compare links
        sed -i.bak -e "s/\[Unreleased\]/\[$next_version\] - $(date -I)/" -e "s/$latest_version...HEAD/$next_version...HEAD\n\[$next_version\]\: $RSH_REPO\/compare\/$latest_version...$next_version/" CHANGELOG.md
        echo "Updated CHANGELOG.md with new version: $next_version"
    else
        err "CHANGELOG.md not found!"
    fi
    "$RSH_PAGER" CHANGELOG.md

    read -p "Continue with this CHANGELOG? (y/N)" confirmation
    case "$confirmation" in
    Y | y | Yes | yes) echo "Continuing…" ;;
    *)
        echo "Cancelled CHANGELOG update."
        mv CHANGELOG.md.bak CHANGELOG.md
        ;;
    esac
}

get_version_info() {
    # Get latest version
    version_prefix="v"
    latest_tag=$(git tag --sort=version:refname | tail -n 1)
    latest_version=${latest_tag#"$version_prefix"}

    # Calculate next version
    IFS='.' read -r major minor patch <<<"$latest_version"
    new_minor=$((minor + 1))
    next_version="$major.$new_minor.0"
    if [ ! -z "${1}" ]; then
        next_version="$1"
    fi

    echo "$latest_version"
    echo "$next_version"
}

check_todos() {
    if ! command -v todo.sh 2>&1 >/dev/null; then
        return
    fi

    if [ $(todo.sh | /usr/bin/tail -n 1 | cut -d ' ' -f 3) -gt 0 ]; then
        read -p "Found TODOs in the code. Are you sure you want to continue? (y/N)" confirmation
        case "$confirmation" in
        Y | y | Yes | yes) echo "Continuing…" ;;
        *)
            err "Cancelled release!"
            ;;
        esac
    fi
}

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo -e "\
Usage: $0 [VERSION]
Publish new release of $RSH_PROJECT

POSITIONAL ARGUMENTS:
    <VERSION>
        Specify version string of release. E.g.

            $0 3.1.4

        If this is not specified, the version number will be calculated as next
        minor version based on the current version number, following Semantic
        Versioning.
        "
    exit 0
else
    main "$@" || exit 1
fi
