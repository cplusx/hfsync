# huggingfacesync (alias: hfsync)

Manifest-driven CLI for syncing files between a local folder and a Hugging Face Hub repo.

## What it does

- Upload files matched by manifest patterns.
- Download files matched by manifest patterns.
- Read default repo config from manifest (`repo_id`, `repo_type`).
- Skip missing local patterns during upload.
- Skip missing remote files during download.

## Authentication

Login before syncing:

```bash
huggingface-cli login
```

Or set token in environment:

```bash
export HF_TOKEN=your_token
```

## Install

```bash
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/cplusx/hfsync.git"
```

Then run:

```bash
huggingfacesync --help
hfsync --help
```

Both command names are available and equivalent:

- `huggingfacesync`
- `hfsync`

If your shell cannot find these commands, use:

```bash
python -m upload_to_hf --help
```

## Manifest format (`.hfupload`)

If `.hfupload` does not exist, `huggingfacesync` (or `hfsync`) will auto-create a template file and exit.
If the file already exists, it is never overwritten.

```txt
# hfsync manifest
# repo_id=<your-namespace>/<your-repo>
# repo_type=dataset

# One glob per line
data/**
artifacts/**/*.json
metadata/*.csv
```

### Config keys

- `repo_id`: Hugging Face repo id, e.g. `alice/my_dataset`.
- `repo_type`: one of `dataset`, `model`, `space` (default: `dataset`).

You can still override from CLI:

```bash
hfsync upload --repo-id alice/another_repo
```

## Usage

```bash
# Upload matched local files
hfsync upload

# Download matched remote files
hfsync download

# Use custom manifest path
hfsync --manifest path/to/.hfupload upload
hfsync --manifest path/to/.hfupload download

# Preview only
hfsync upload --dry-run
hfsync download --dry-run
```

### Large upload strategy

`upload` supports automatic switching to `upload_large_folder`:

```bash
# default: auto
hfsync upload

# force large-folder uploader
hfsync upload --large-upload always

# force regular uploader
hfsync upload --large-upload never
```

Auto mode switches to large uploader when either threshold is exceeded:

- `--large-files-threshold` (default `3000`)
- `--large-bytes-threshold` (default `1000000000`)

You can also set `--large-num-workers` for `upload_large_folder`.

## Notes

- Upload uses explicit matched files, so patterns that match nothing are reported and skipped.
- Download first lists remote files then filters with manifest patterns.
- Keep `.hfupload` under version control for reproducible sync behavior.

## Release to PyPI

### One-time setup

1. In PyPI project settings, create a **Trusted Publisher** for this GitHub repo/workflow.
2. Use the exact repository and workflow file: `.github/workflows/publish.yml`.

### Publish a new version

```bash
# from repo root
./scripts/release.sh 0.1.3
```

This script will:

- update versions in `pyproject.toml` and `setup.py`
- build and run `twine check`
- commit + create tag `v<version>` + push
- trigger GitHub Actions publish workflow

The workflow file is at `.github/workflows/publish.yml`.
