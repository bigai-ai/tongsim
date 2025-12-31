from __future__ import annotations

import argparse
import os
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

DEFAULT_HF_DATASET = "bigai/tongsim-unreal-content"
DEFAULT_WINDOWS_CACHE_DIR_NAME = "hf"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download TongSIM Unreal Engine Content assets from Hugging Face and "
            "place them into this repo's `unreal/Content/` directory."
        ),
    )
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_HF_DATASET,
        help=f"Hugging Face dataset repo id (default: {DEFAULT_HF_DATASET}).",
    )
    parser.add_argument(
        "--revision",
        default=None,
        help="Dataset revision (branch/tag/commit). Defaults to the dataset default branch.",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help=(
            "Hugging Face hub cache directory. On Windows, using a short path can avoid "
            "MAX_PATH/symlink errors (example: D:\\hf)."
        ),
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Target directory (default: <repo>/unreal/Content).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing files in the target directory (except README.md).",
    )
    return parser.parse_args()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_target_dir() -> Path:
    return _repo_root() / "unreal" / "Content"


def _resolve_cache_dir(cache_dir: str | None) -> Path | None:
    if cache_dir:
        candidate = Path(cache_dir).expanduser()
        if not candidate.is_absolute():
            candidate = _repo_root() / candidate
        candidate = candidate.resolve()
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate

    if os.name != "nt":
        return None

    repo_root = _repo_root()
    candidates = [
        Path(repo_root.anchor) / DEFAULT_WINDOWS_CACHE_DIR_NAME,
        repo_root / ".cache" / DEFAULT_WINDOWS_CACHE_DIR_NAME,
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        return candidate.resolve()

    return None


def _target_has_payload(target_dir: Path) -> bool:
    if not target_dir.exists():
        return False
    for child in target_dir.iterdir():
        if child.name == "README.md":
            continue
        return True
    return False


def _clear_target_dir(target_dir: Path) -> None:
    if not target_dir.exists():
        return
    for child in target_dir.iterdir():
        if child.name == "README.md":
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def _copy_tree_contents(source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in source_dir.iterdir():
        dst = target_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst)


def _locate_content_dir(root: Path) -> Path | None:
    candidates = [
        root / "Content",
        root / "unreal" / "Content",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _extract_archive(archive_path: Path, extract_root: Path) -> Path:
    extract_root = extract_root.resolve()

    def is_within_directory(target_path: Path) -> bool:
        target_path = target_path.resolve()
        return os.path.commonpath([str(extract_root), str(target_path)]) == str(extract_root)

    if archive_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive_path) as zf:
            for member in zf.infolist():
                candidate = extract_root / member.filename
                if not is_within_directory(candidate):
                    raise ValueError(f"Unsafe zip member path: {member.filename}")
            zf.extractall(extract_root)
        return extract_root

    suffixes = "".join(archive_path.suffixes).lower()
    if suffixes.endswith(".tar.gz") or suffixes.endswith(".tgz") or suffixes.endswith(".tar"):
        with tarfile.open(archive_path) as tf:
            for member in tf.getmembers():
                if member.islnk() or member.issym():
                    raise ValueError(f"Refusing to extract links from tar: {member.name}")
                candidate = extract_root / member.name
                if not is_within_directory(candidate):
                    raise ValueError(f"Unsafe tar member path: {member.name}")
            tf.extractall(extract_root)
        return extract_root

    raise ValueError(f"Unsupported archive format: {archive_path.name}")


def _find_archive(snapshot_dir: Path) -> Path | None:
    patterns = ["*.zip", "*.tar", "*.tar.gz", "*.tgz"]
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(snapshot_dir.glob(pattern))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.name.lower())
    return candidates[0]


def main() -> int:
    args = _parse_args()
    target_dir = Path(args.target).resolve() if args.target else _default_target_dir()

    try:
        from huggingface_hub import snapshot_download
    except ModuleNotFoundError:
        print(
            "Missing dependency: huggingface_hub\n"
            "Install it with one of:\n"
            "  pip install huggingface_hub\n"
            "  uv pip install huggingface_hub\n",
            file=sys.stderr,
        )
        return 1

    cache_dir = _resolve_cache_dir(args.cache_dir)
    if _target_has_payload(target_dir) and not args.force:
        print(
            f"Refusing to overwrite non-empty target directory: {target_dir}\n"
            "Use --force to remove existing files (except README.md).",
            file=sys.stderr,
        )
        return 2

    print(f"Downloading dataset snapshot: {args.repo_id} (type=dataset)")
    if cache_dir is not None:
        print(f"Using Hugging Face cache dir: {cache_dir}")
    download_kwargs: dict[str, object] = {
        "repo_id": args.repo_id,
        "repo_type": "dataset",
        "revision": args.revision,
    }
    if cache_dir is not None:
        download_kwargs["cache_dir"] = str(cache_dir)
    snapshot_dir = Path(
        snapshot_download(**download_kwargs)
    )
    print(f"Snapshot ready: {snapshot_dir}")

    source_dir = _locate_content_dir(snapshot_dir)
    if source_dir is None:
        archive = _find_archive(snapshot_dir)
        if archive is None:
            print(
                "Could not find `Content/` (or `unreal/Content/`) in the dataset snapshot, "
                "and no supported archive was found at the dataset root.\n"
                f"Looked in: {snapshot_dir}",
                file=sys.stderr,
            )
            return 3

        print(f"Extracting archive: {archive.name}")
        with tempfile.TemporaryDirectory(prefix="tongsim_unreal_content_") as tmp:
            extracted_root = Path(tmp)
            _extract_archive(archive, extracted_root)
            source_dir = _locate_content_dir(extracted_root) or extracted_root

    print(f"Installing Content into: {target_dir}")
    _clear_target_dir(target_dir)
    _copy_tree_contents(source_dir, target_dir)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
