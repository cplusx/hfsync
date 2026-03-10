# Maintainer Notes

This document is for project maintainers (not end users).

## Release Automation

This repo uses two workflows:

- `.github/workflows/release-please.yml`: auto-bumps version and creates tags/releases from commits on `main`.
- `.github/workflows/publish.yml`: publishes to PyPI when a tag `v*` is pushed.

### Commit style

Use conventional commit prefixes so Release Please can decide version bumps:

- `fix: ...` -> patch bump
- `feat: ...` -> minor bump
- `feat!: ...` or `BREAKING CHANGE:` -> major bump

### First run behavior

Release Please may open a "Release PR" first. After that PR is merged, it will create a tag and GitHub release, which then triggers PyPI publish.

## Manual PyPI Publishing (fallback)

### One-time setup

1. Create a PyPI API token.
2. Add repository secret `PYPI_API_TOKEN` in GitHub Actions secrets.

### Release

```bash
# from repo root
./scripts/release.sh 0.1.4
```

The script will:

- update versions in `pyproject.toml` and `setup.py`
- build distributions
- run `twine check`
- commit, tag (`v<version>`), and push
- trigger `.github/workflows/publish.yml`
