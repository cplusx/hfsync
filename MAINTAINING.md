# Maintainer Notes

This document is for project maintainers (not end users).

## PyPI Publishing

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
