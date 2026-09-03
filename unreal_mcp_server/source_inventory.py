"""Deterministic source inventory for qualified UnrealMCP plugin builds."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SOURCE_INVENTORY_SCHEMA = "unreal_mcp_ghost.source_inventory.v1"


@dataclass(frozen=True)
class SourceInventoryEntry:
    path: str
    size: int
    sha256: str

    def as_dict(self) -> dict[str, object]:
        return {"path": self.path, "size": self.size, "sha256": self.sha256}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _source_files(plugin_root: Path) -> Iterable[Path]:
    descriptor = plugin_root / "UnrealMCP.uplugin"
    if not descriptor.is_file() or descriptor.is_symlink():
        raise ValueError(f"UnrealMCP descriptor is missing or unsafe: {descriptor}")
    yield descriptor

    for relative_directory in ("Config", "Source"):
        directory = plugin_root / relative_directory
        if not directory.exists():
            if relative_directory == "Source":
                raise ValueError(f"UnrealMCP source directory is missing: {directory}")
            continue
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError(f"UnrealMCP inventory directory is unsafe: {directory}")
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"UnrealMCP source inventory contains a link: {path}")
            if path.is_file():
                yield path


def build_source_inventory(plugin_root: Path) -> dict[str, object]:
    """Hash the exact descriptor, Config, and Source files for one plugin tree."""

    root = plugin_root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"UnrealMCP plugin root does not exist: {root}")

    entries: list[SourceInventoryEntry] = []
    for path in _source_files(root):
        relative_path = path.relative_to(root).as_posix()
        content = path.read_bytes()
        entries.append(
            SourceInventoryEntry(
                path=relative_path,
                size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
            )
        )
    entries.sort(key=lambda entry: entry.path)

    digest_payload = {
        "schema": SOURCE_INVENTORY_SCHEMA,
        "files": [entry.as_dict() for entry in entries],
    }
    inventory_sha256 = hashlib.sha256(_canonical_bytes(digest_payload)).hexdigest()
    return {
        **digest_payload,
        "plugin_root": str(root),
        "file_count": len(entries),
        "total_bytes": sum(entry.size for entry in entries),
        "inventory_sha256": inventory_sha256,
    }
