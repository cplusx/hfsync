#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download, snapshot_download
from huggingface_hub.utils import EntryNotFoundError

DEFAULT_MANIFEST_TEMPLATE = """# hfsync manifest
# Uncomment and set your target repo:
# repo_id=your-namespace/your-repo
# repo_type=dataset
#
# One glob pattern per line (relative to current directory):
# data/**
# outputs/**/*.json
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sync files between local folder and a Hugging Face dataset repo "
            "using patterns from a manifest file."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(".hfupload"),
        help="Manifest file containing repo config and glob patterns.",
    )

    subparsers = parser.add_subparsers(dest="action", required=True)

    def add_common_args(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--repo-id",
            type=str,
            default=None,
            help="Override Hugging Face repo id. If omitted, read from manifest.",
        )
        p.add_argument(
            "--repo-type",
            type=str,
            default=None,
            choices=["dataset", "model", "space"],
            help="Override repo type. If omitted, read from manifest (default: dataset).",
        )
        p.add_argument(
            "--root",
            type=Path,
            default=Path("."),
            help="Local root directory to upload/download.",
        )
        p.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print parsed plan and exit.",
        )

    upload_p = subparsers.add_parser("upload", help="Upload files matched by manifest patterns.")
    add_common_args(upload_p)
    upload_p.add_argument(
        "--message",
        type=str,
        default="Upload files from .hfupload manifest",
        help="Commit message on Hugging Face hub.",
    )
    upload_p.add_argument(
        "--private",
        action="store_true",
        help="Create repo as private if it does not exist.",
    )
    upload_p.add_argument(
        "--large-upload",
        type=str,
        default="auto",
        choices=["auto", "always", "never"],
        help="Use upload_large_folder strategy: auto (by thresholds), always, or never.",
    )
    upload_p.add_argument(
        "--large-files-threshold",
        type=int,
        default=3000,
        help="Auto mode: switch to large upload when matched file count exceeds this.",
    )
    upload_p.add_argument(
        "--large-bytes-threshold",
        type=int,
        default=1_000_000_000,
        help="Auto mode: switch to large upload when total matched bytes exceeds this.",
    )
    upload_p.add_argument(
        "--large-num-workers",
        type=int,
        default=None,
        help="Optional worker count for upload_large_folder.",
    )

    download_p = subparsers.add_parser("download", help="Download files matched by manifest patterns.")
    add_common_args(download_p)
    download_p.add_argument(
        "--large-download",
        type=str,
        default="auto",
        choices=["auto", "always", "never"],
        help="Use snapshot_download strategy: auto (by thresholds), always, or never.",
    )
    download_p.add_argument(
        "--download-files-threshold",
        type=int,
        default=2000,
        help="Auto mode: switch to snapshot_download when matched remote file count exceeds this.",
    )
    download_p.add_argument(
        "--download-num-workers",
        type=int,
        default=8,
        help="Worker count for snapshot_download in large-download mode.",
    )
    download_p.add_argument(
        "--skip-unchanged-local",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Skip downloading files that already exist locally with the same file size. "
            "Enabled by default; disable with --no-skip-unchanged-local."
        ),
    )

    return parser.parse_args()


def load_manifest(manifest: Path) -> tuple[dict[str, str], list[str]]:
    if not manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest}")
    config: dict[str, str] = {}
    patterns: list[str] = []
    for raw in manifest.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip().lower()
            value = value.strip()
            if key in {"repo_id", "repo_type"}:
                config[key] = value
                continue
        patterns.append(line)
    if not patterns:
        raise ValueError(f"No patterns found in manifest: {manifest}")
    return config, patterns


def ensure_manifest_exists(manifest: Path) -> bool:
    if manifest.exists():
        return False
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(DEFAULT_MANIFEST_TEMPLATE)
    return True


def match_any(path_str: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path_str, pat) for pat in patterns)


def resolve_local_files(root: Path, patterns: list[str]) -> tuple[list[str], list[str]]:
    matched_files: set[str] = set()
    missing_patterns: list[str] = []

    for pat in patterns:
        has_match = False
        for p in root.glob(pat):
            if p.is_file():
                matched_files.add(p.relative_to(root).as_posix())
                has_match = True
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        matched_files.add(f.relative_to(root).as_posix())
                        has_match = True
        if not has_match:
            missing_patterns.append(pat)

    return sorted(matched_files), missing_patterns


def format_bytes(num: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f}{unit}"
        value /= 1024
    return f"{num}B"


def choose_large_upload(
    mode: str,
    file_count: int,
    total_bytes: int,
    file_threshold: int,
    byte_threshold: int,
) -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    return file_count > file_threshold or total_bytes > byte_threshold


def choose_large_download(mode: str, file_count: int, file_threshold: int) -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    return file_count > file_threshold


def compute_skip_unchanged(
    root: Path, dry_run_infos: list
) -> tuple[list[str], int]:
    to_download: list[str] = []
    skipped = 0
    for info in dry_run_infos:
        rel = info.filename
        local_path = root / rel
        if local_path.exists():
            try:
                if local_path.stat().st_size == int(info.file_size):
                    skipped += 1
                    continue
            except OSError:
                pass
        to_download.append(rel)
    return to_download, skipped


def run_upload(api: HfApi, args: argparse.Namespace, repo_id: str, repo_type: str, patterns: list[str]) -> None:
    files_to_upload, missing_patterns = resolve_local_files(args.root, patterns)

    if missing_patterns:
        print("Skipped missing local patterns:")
        for p in missing_patterns:
            print(f"  - {p}")

    if not files_to_upload:
        print("No local files matched. Nothing to upload.")
        return

    total_bytes = sum((args.root / rel).stat().st_size for rel in files_to_upload)
    use_large = choose_large_upload(
        mode=args.large_upload,
        file_count=len(files_to_upload),
        total_bytes=total_bytes,
        file_threshold=args.large_files_threshold,
        byte_threshold=args.large_bytes_threshold,
    )
    selected = "upload_large_folder" if use_large else "upload_folder"
    print(
        "Matched local files for upload: "
        f"{len(files_to_upload)} (total={format_bytes(total_bytes)})"
    )
    print(
        f"Selected strategy: {selected} "
        f"(mode={args.large_upload}, file_threshold={args.large_files_threshold}, "
        f"byte_threshold={args.large_bytes_threshold})"
    )
    if args.dry_run:
        return

    api.create_repo(
        repo_id=repo_id,
        repo_type=repo_type,
        private=args.private,
        exist_ok=True,
    )
    if use_large:
        api.upload_large_folder(
            repo_id=repo_id,
            repo_type=repo_type,
            folder_path=str(args.root),
            allow_patterns=files_to_upload,
            num_workers=args.large_num_workers,
        )
    else:
        api.upload_folder(
            repo_id=repo_id,
            repo_type=repo_type,
            folder_path=str(args.root),
            path_in_repo=".",
            allow_patterns=files_to_upload,
            commit_message=args.message,
        )
    print("Upload completed.")


def run_download(api: HfApi, args: argparse.Namespace, repo_id: str, repo_type: str, patterns: list[str]) -> None:
    repo_files = api.list_repo_files(repo_id=repo_id, repo_type=repo_type)
    matched_remote = [f for f in repo_files if match_any(f, patterns)]
    missing_patterns = [p for p in patterns if not any(fnmatch.fnmatch(f, p) for f in repo_files)]

    if missing_patterns:
        print("Skipped missing remote patterns:")
        for p in missing_patterns:
            print(f"  - {p}")

    print(f"Matched remote files for download: {len(matched_remote)}")
    use_large = choose_large_download(
        mode=args.large_download,
        file_count=len(matched_remote),
        file_threshold=args.download_files_threshold,
    )
    selected = "snapshot_download" if use_large else "hf_hub_download(loop)"
    print(
        f"Selected strategy: {selected} "
        f"(mode={args.large_download}, file_threshold={args.download_files_threshold})"
    )

    dry_run_infos = snapshot_download(
        repo_id=repo_id,
        repo_type=repo_type,
        allow_patterns=patterns,
        local_dir=str(args.root),
        dry_run=True,
    )
    expected_total = len(dry_run_infos)
    to_download = [info.filename for info in dry_run_infos]
    skipped_unchanged = 0
    if args.skip_unchanged_local:
        to_download, skipped_unchanged = compute_skip_unchanged(args.root, dry_run_infos)
        print(
            f"Incremental filter: expected={expected_total}, "
            f"to_download={len(to_download)}, skipped_unchanged={skipped_unchanged}"
        )

    if args.dry_run:
        return

    if not to_download:
        print(
            f"Download completed. downloaded=0, skipped_missing=0, "
            f"skipped_unchanged={skipped_unchanged}"
        )
        return

    args.root.mkdir(parents=True, exist_ok=True)
    if use_large:
        snapshot_download(
            repo_id=repo_id,
            repo_type=repo_type,
            allow_patterns=to_download,
            local_dir=str(args.root),
            local_dir_use_symlinks=False,
            max_workers=args.download_num_workers,
        )
        print(
            "Download completed via snapshot_download. "
            f"downloaded={len(to_download)}, skipped_unchanged={skipped_unchanged}"
        )
        return

    downloaded = 0
    skipped_missing = 0
    to_download_set = set(to_download)
    for file_in_repo in matched_remote:
        if file_in_repo not in to_download_set:
            continue
        try:
            hf_hub_download(
                repo_id=repo_id,
                repo_type=repo_type,
                filename=file_in_repo,
                local_dir=str(args.root),
                local_dir_use_symlinks=False,
            )
            downloaded += 1
        except EntryNotFoundError:
            skipped_missing += 1
            print(f"Skipped missing remote file: {file_in_repo}")

    print(
        "Download completed. "
        f"downloaded={downloaded}, skipped_missing={skipped_missing}, "
        f"skipped_unchanged={skipped_unchanged}"
    )


def main() -> None:
    args = parse_args()
    created = ensure_manifest_exists(args.manifest)
    if created:
        print(f"Created manifest template: {args.manifest}")
        print("Edit it first (set repo_id + patterns), then rerun the command.")
        return

    try:
        config, patterns = load_manifest(args.manifest)
    except ValueError as exc:
        print(str(exc))
        print("Please update your manifest and rerun.")
        return

    repo_id = args.repo_id or config.get("repo_id")
    repo_type = args.repo_type or config.get("repo_type", "dataset")
    if not repo_id:
        raise ValueError("repo_id is required. Set it in .hfupload (repo_id=...) or pass --repo-id.")

    print(f"action={args.action}")
    print(f"repo_id={repo_id}")
    print(f"repo_type={repo_type}")
    print(f"manifest={args.manifest}")
    print("patterns:")
    for p in patterns:
        print(f"  - {p}")

    api = HfApi()
    if args.action == "upload":
        run_upload(api, args, repo_id, repo_type, patterns)
    else:
        run_download(api, args, repo_id, repo_type, patterns)


if __name__ == "__main__":
    main()
