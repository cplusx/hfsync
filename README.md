# hfsync

Manifest-driven Hugging Face sync CLI.

## Install

```bash
pip install "git+https://github.com/cplusx/hfsync.git"
```

## Manifest

Create `.hfupload` in your project root:

```txt
repo_id=yourname/your_dataset_repo
repo_type=dataset

# glob patterns
HED-BSDS/images/**
BSDS/reasoning/**
```

## Usage

```bash
# upload files matched by manifest
hfsync upload

# download files matched by manifest
hfsync download

# custom manifest path
hfsync --manifest path/to/.hfupload upload

# dry run
hfsync upload --dry-run
```

## Notes

- Missing local patterns are skipped in upload mode.
- Missing remote files are skipped in download mode.
