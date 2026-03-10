#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <version>" >&2
  echo "Example: $0 0.1.3" >&2
  exit 1
fi

VERSION="$1"
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Version must look like x.y.z" >&2
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Working tree is not clean. Commit or stash changes first." >&2
  exit 1
fi

python3 - <<PY
from pathlib import Path
import re
v = "${VERSION}"

pyproject = Path("pyproject.toml")
setup = Path("setup.py")

s = pyproject.read_text()
s2, n = re.subn(r'(?m)^version\s*=\s*"[^"]+"\s*$', f'version = "{v}"', s, count=1)
if n != 1:
    raise SystemExit("Failed to update version in pyproject.toml")
pyproject.write_text(s2)

s = setup.read_text()
s2, n = re.subn(r'(?m)^\s*version\s*=\s*"[^"]+",\s*$', f'    version="{v}",', s, count=1)
if n != 1:
    raise SystemExit("Failed to update version in setup.py")
setup.write_text(s2)
PY

rm -rf build dist *.egg-info
python3 -m pip install --upgrade build twine
python3 -m build
python3 -m twine check dist/*

git add pyproject.toml setup.py
git commit -m "Release v${VERSION}"
git tag "v${VERSION}"
git push origin main
git push origin "v${VERSION}"

echo "Done. Release tag v${VERSION} pushed. GitHub Actions will publish to PyPI."
