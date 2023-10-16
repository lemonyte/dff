from __future__ import annotations

import fnmatch
import functools
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Optional

from rich.console import Console
from rich.progress import MofNCompleteColumn, Progress
from typer import Option, Typer

EMPTY_HASH = bytes.fromhex("d41d8cd98f00b204e9800998ecf8427e")

MATCH_SEP = r"(?:/|\\)"
MATCH_SEP_OR_END = r"(?:/|\\|\Z)"
MATCH_NON_RECURSIVE = r"[^/\\]*"
MATCH_RECURSIVE = r"(?:.*)"

app = Typer(invoke_without_command=True, no_args_is_help=True)
entrypoint = functools.partial(app, windows_expand_args=False)


@dataclass
class FileInfo:
    path: Path
    size: int
    hash: bytes | None


class HashType(StrEnum):
    FULL = "full"
    PARTIAL = "partial"


class CompareMethod(StrEnum):
    SIZE = "size"
    PARTIAL_HASH = "partial-hash"
    HASH = "hash"


class OutputFormat(StrEnum):
    JSON = "json"
    LIST = "list"


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
    flags = re.IGNORECASE if os.name == "nt" else 0
    match = bool(re.fullmatch(glob_to_re(pattern), str(path), flags=flags))
    if pattern.endswith(("/", "\\")):
        return match and path.is_dir()
    return match


def get_files(dirs: list[Path], exclude: list[str]) -> list[FileInfo]:
    files = []
    for dir in dirs:
        for dirname, _, filenames in os.walk(dir):
            for filename in filenames:
                path = Path(dirname, filename)
                if any(match_glob(path, pattern) for pattern in exclude):
                    continue
                files.append(FileInfo(path=path, size=path.stat().st_size, hash=None))
    return files


def hash_file(file_info: FileInfo, hash_type: HashType = HashType.FULL, chunk_size: int = 64 * 1024) -> bytes:
    if file_info.size == 0:
        return EMPTY_HASH
    if file_info.hash and file_info.size < chunk_size * 3:
        return file_info.hash
    hasher = hashlib.md5(usedforsecurity=False)
    with file_info.path.open("rb") as file:
        if hash_type is HashType.FULL or file_info.size <= chunk_size * 3:
            hasher.update(file.read())
        elif hash_type is HashType.PARTIAL:
            hasher.update(file.read(chunk_size))
            file.seek((file_info.size // 2) - (chunk_size // 2), os.SEEK_SET)
            hasher.update(file.read(chunk_size))
            file.seek(-chunk_size, os.SEEK_END)
            hasher.update(file.read(chunk_size))
    return hasher.digest()


@app.callback()
def main(
    *,
    dirs: list[Path],  # TODO: fix other options taken as paths
    exclude: Annotated[
        Optional[list[str]],  # noqa: UP007; Typer does not support "Type | None" syntax
        Option(help="Exclude files matching this glob pattern."),
    ] = None,
    compare_method: CompareMethod = CompareMethod.HASH,
    output_format: OutputFormat = OutputFormat.JSON,
    fail_on_duplicate: Annotated[bool, Option(help="Exit with error code 1 if duplicates are found.")] = False,
) -> None:
    dirs = [path.expanduser() for path in dirs]
    dirs = [path for path in dirs if path.exists() and path.is_dir()]
    exclude = exclude or []
    # Typer does not support IntEnums, so we need to convert manually.
    compare_methods = list(CompareMethod)
    compare_method_index = compare_methods.index(compare_method)
    console = Console(stderr=True)
    start_time = time.perf_counter()
    sorted: dict[int | bytes, list[FileInfo]] = {}

    with Progress(*Progress.get_default_columns(), MofNCompleteColumn(), console=console) as progress:
        task = progress.add_task("Searching for files", total=None)
        files = get_files(dirs, exclude)
        progress.update(task, total=len(files), completed=len(files))
    total = len(files)
    console.print(f"Found {total} files.")

    for file in files:
        sorted.setdefault(file.size, []).append(file)
    files = [item for items in sorted.values() if len(items) > 1 for item in items]
    console.print(f"Found {len(files)} files with matching sizes.")

    if compare_method_index >= compare_methods.index(CompareMethod.PARTIAL_HASH):
        sorted.clear()
        if files:
            with Progress(*Progress.get_default_columns(), MofNCompleteColumn(), console=console) as progress:
                task = progress.add_task("Calculating partial hashes", total=len(files))
                for file in files:
                    hash = hash_file(file, HashType.PARTIAL)
                    file.hash = hash
                    sorted.setdefault(file.hash, []).append(file)
                    progress.advance(task)
            files = [item for items in sorted.values() if len(items) > 1 for item in items]
            console.print(f"Found {len(files)} files with partial hashes that match other files.")

    if compare_method_index >= compare_methods.index(CompareMethod.HASH):
        sorted.clear()
        if files:
            with Progress(*Progress.get_default_columns(), MofNCompleteColumn(), console=console) as progress:
                task = progress.add_task("Calculating full hashes", total=len(files))
                for file in files:
                    hash = hash_file(file, HashType.FULL)
                    file.hash = hash
                    sorted.setdefault(file.hash, []).append(file)
                    progress.advance(task)
            files = [item for items in sorted.values() if len(items) > 1 for item in items]
            console.print(f"Found {len(files)} files with hashes that match other files.")

    total_time = time.perf_counter() - start_time
    console.print(
        f"Found {len(files)} duplicate files in {total_time:.4f} seconds"
        f" ({len(files) / total:.2%} of all files).",
    )
    output = [
        {
            "hash": key.hex() if isinstance(key, bytes) else None,
            "size": files[0].size,
            "paths": [str(file.path) for file in files],
        }
        for key, files in sorted.items()
        if len(files) > 1
    ]
    output.sort(key=lambda item: item["size"])
    if output_format is OutputFormat.JSON:
        json.dump(output, sys.stdout, indent=2)
    elif output_format is OutputFormat.LIST:
        for item in output:
            print("\n", item["hash"] if item["hash"] else item["size"])
            for path in item["paths"]:
                print(f"  {path}")
    raise SystemExit(int(fail_on_duplicate))
