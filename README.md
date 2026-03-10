# hfsync

Manifest-driven CLI for syncing files between a local folder and a Hugging Face Hub repo.

## What it does

- Upload files matched by manifest patterns.
- Download files matched by manifest patterns.
- Read default repo config from manifest (`repo_id`, `repo_type`).
- Skip missing local patterns during upload.
- Skip missing remote files during download.

## Recommended environment

Use an isolated Python environment (Conda or venv) instead of installing into system Python.

```bash
# Conda example
conda create -n hfsync-env python=3.10 -y
conda activate hfsync-env
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/cplusx/hfsync.git"
```

Then run via module entry script installed in that env:

```bash
hfsync --help
```

If your shell cannot find `hfsync`, use:

```bash
python -m upload_to_hf --help
```

## Manifest format (`.hfupload`)

Create a manifest file in your project root (or pass another path with `--manifest`).

```txt
# Optional config
repo_id=<your-namespace>/<your-repo>
repo_type=dataset

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

## Authentication

Login once before syncing:

```bash
huggingface-cli login
```

Or set token in environment:

```bash
export HF_TOKEN=your_token
```

## Notes

- Upload uses explicit matched files, so patterns that match nothing are reported and skipped.
- Download first lists remote files then filters with manifest patterns.
- Keep `.hfupload` under version control for reproducible sync behavior.
