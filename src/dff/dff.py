import fnmatch
import functools
import hashlib
import json
import os
import re
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

from rich.console import Console
from rich.progress import MofNCompleteColumn, Progress
from typer import Option, Typer

app = Typer(invoke_without_command=True, no_args_is_help=True)
entrypoint = functools.partial(app, windows_expand_args=False)

EMPTY_HASH = bytes.fromhex("d41d8cd98f00b204e9800998ecf8427e")

MATCH_SEP = r"(?:/|\\)"
MATCH_SEP_OR_END = r"(?:/|\\|\Z)"
MATCH_NON_RECURSIVE = r"[^/\\]*"
MATCH_RECURSIVE = r"(?:.*)"


class HashType(Enum):
    FULL = "full"
    PARTIAL = "partial"


def glob_to_re(pattern: str) -> str:
    """Translate a glob pattern to a regular expression for matching."""
    fragments: list[str] = []
    for segment in re.split(r"/|\\", pattern):
        if segment == "":
            continue
        if segment == "**":
            # Remove previous separator match, so the recursive match can match zero or more segments.
            if fragments and fragments[-1] == MATCH_SEP:
                fragments.pop()
            fragments.append(MATCH_RECURSIVE)
        elif "**" in segment:
            msg = "invalid pattern: '**' can only be an entire path component"
            raise ValueError(msg)
        else:
            fragment = fnmatch.translate(segment)
            fragment = fragment.replace(r"(?s:", r"(?:")
            fragment = fragment.replace(r".*", MATCH_NON_RECURSIVE)
            fragment = fragment.replace(r"\Z", r"")
            fragments.append(fragment)
        fragments.append(MATCH_SEP)
    # Remove trailing MATCH_SEP, so it can be replaced with MATCH_SEP_OR_END.
    if fragments and fragments[-1] == MATCH_SEP:
        fragments.pop()
    fragments.append(MATCH_SEP_OR_END)
    return rf"(?s:{''.join(fragments)})"


def match_glob(path: Path, pattern: str) -> bool:
    """Check if a path matches a glob pattern.

    If the pattern ends with a directory separator, the path must be a directory.
    """
    match = bool(re.fullmatch(glob_to_re(pattern), str(path)))
    if pattern.endswith(("/", "\\")):
        return match and path.is_dir()
    return match


def get_file_paths(dirs: list[Path], exclude: list[str]) -> list[Path]:
    files = []
    for dir in dirs:
        for dirname, _, filenames in os.walk(dir):
            for filename in filenames:
                path = Path(dirname, filename)
                if any(match_glob(path, pattern) for pattern in exclude):
                    continue
                files.append(path)
    return files


def hash_file(path: Path, hash_type: HashType = HashType.FULL, chunk_size: int = 64 * 1024) -> bytes:
    size = path.stat().st_size
    if size == 0:
        return EMPTY_HASH
    # TODO: return already calculated hash when file info struct is implemented.
    hasher = hashlib.md5()  # noqa: S324
    with path.open("rb") as file:
        if hash_type is HashType.FULL or size <= chunk_size * 3:
            hasher.update(file.read())
        elif hash_type is HashType.PARTIAL:
            hasher.update(file.read(chunk_size))
            file.seek((size // 2) - (chunk_size // 2), os.SEEK_SET)
            hasher.update(file.read(chunk_size))
            file.seek(-chunk_size, os.SEEK_END)
            hasher.update(file.read(chunk_size))
    return hasher.digest()


@app.callback()
def main(
    *,
    dirs: list[Path],  # TODO: fix other options taken as paths
    exclude: Annotated[
        Optional[list[str]],  # noqa: FA100, Typer does not support "Type | None" syntax
        Option(help="Exclude files matching this glob pattern."),
    ] = None,
    fail_on_duplicate: Annotated[bool, Option(help="Exit with error code 1 if duplicates are found.")] = False,
) -> None:
    exclude = exclude or []
    console = Console(stderr=True)
    dirs = [path.expanduser() for path in dirs]
    dirs = [path for path in dirs if path.exists() and path.is_dir()]
    start_time = time.perf_counter()

    with Progress(*Progress.get_default_columns(), MofNCompleteColumn(), console=console) as progress:
        task = progress.add_task("Searching for files", total=None)
        all_files = get_file_paths(dirs, exclude)
        progress.update(task, total=len(all_files), completed=len(all_files))
    console.print(f"Found {len(all_files)} files.")

    sizes: dict[int, list[Path]] = {}
    with Progress(*Progress.get_default_columns(), MofNCompleteColumn(), console=console) as progress:
        task = progress.add_task("Checking file sizes", total=len(all_files))
        for file in all_files:
            sizes.setdefault(file.stat().st_size, []).append(file)
            progress.advance(task)
    files = [item for items in sizes.values() if len(items) > 1 for item in items]
    console.print(f"Found {len(files)} files with matching sizes.")

    minihashes: dict[bytes, list[Path]] = {}
    if files:
        with Progress(*Progress.get_default_columns(), MofNCompleteColumn(), console=console) as progress:
            task = progress.add_task("Minihashing files", total=len(files))
            for file in files:
                minihashes.setdefault(hash_file(file, HashType.PARTIAL), []).append(file)
                progress.advance(task)
        files = [item for items in minihashes.values() if len(items) > 1 for item in items]
        skipped = len(minihashes.get(b"", []))
        matching_minihash = len(files) - skipped
        if matching_minihash:
            console.print(f"Found {matching_minihash} files with minihashes that match other files.")
        if skipped:
            console.print(f"Skipped minihashing {skipped} files because they are too small.")

    hashes: dict[bytes, list[Path]] = {}
    if files:
        with Progress(*Progress.get_default_columns(), MofNCompleteColumn(), console=console) as progress:
            task = progress.add_task("Hashing files", total=len(files))
            for file in files:
                hashes.setdefault(hash_file(file, HashType.FULL), []).append(file)
                progress.advance(task)
        files = [item for items in hashes.values() if len(items) > 1 for item in items]
    duplicate = len(files)

    total_time = time.perf_counter() - start_time
    if duplicate:
        console.print(
            f"Found {duplicate} duplicate files in {total_time:.4f} seconds"
            f" ({duplicate / len(all_files):.2%} of all files).",
        )
    if EMPTY_HASH in hashes:
        console.print(f"{len(hashes.get(EMPTY_HASH, ()))} out of {duplicate} files are empty files.")

    output = [
        {
            "hash": hash.hex(),
            "size": paths[0].stat().st_size,
            "files": [str(item) for item in paths],
        }
        for hash, paths in hashes.items()
        if len(paths) > 1
    ]
    output.sort(key=lambda item: item["size"])
    json.dump(output, sys.stdout, indent=2)
    raise SystemExit(int(fail_on_duplicate))
