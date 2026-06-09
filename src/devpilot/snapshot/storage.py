"""Snapshot storage — save/load snapshots as JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from devpilot.snapshot.capture import Snapshot

SNAPSHOT_DIR: Path = Path.home() / ".config" / "devpilot" / "snapshots"


def _ensure_dir() -> None:
    """Create the snapshot directory if it does not exist."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_name(name: str) -> str:
    """Replace path-unsafe characters in snapshot names.

    Args:
        name: Raw snapshot name.

    Returns:
        Sanitized name safe for use in filenames.
    """
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


def save_snapshot(snapshot: Snapshot) -> Path:
    """Save a snapshot to a JSON file.

    Filename format: <sanitized_name>_<timestamp>.json

    Args:
        snapshot: The snapshot to persist.

    Returns:
        Path to the saved snapshot file.
    """
    _ensure_dir()
    safe_name = _sanitize_name(snapshot.name)
    safe_timestamp = snapshot.timestamp.replace(":", "-")
    filename = f"{safe_name}_{safe_timestamp}.json"
    filepath = SNAPSHOT_DIR / filename

    data = _snapshot_to_dict(snapshot)
    filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return filepath


def _snapshot_to_dict(snapshot: Snapshot) -> dict[str, Any]:
    """Convert a Snapshot to a plain dict for JSON serialization.

    Args:
        snapshot: The snapshot to convert.

    Returns:
        Dictionary representation.
    """
    return {
        "name": snapshot.name,
        "timestamp": snapshot.timestamp,
        "devpilot_version": snapshot.devpilot_version,
        "system": snapshot.system,
        "installed_apt_packages": snapshot.installed_apt_packages,
        "git_config": snapshot.git_config,
        "environment_variables": snapshot.environment_variables,
        "config_files": snapshot.config_files,
        "devpilot_config": snapshot.devpilot_config,
    }


def _dict_to_snapshot(data: dict[str, Any]) -> Snapshot:
    """Convert a plain dict back to a Snapshot.

    Args:
        data: Dictionary with snapshot fields.

    Returns:
        Reconstructed Snapshot instance.
    """
    return Snapshot(
        name=data.get("name", "unknown"),
        timestamp=data.get("timestamp", ""),
        devpilot_version=data.get("devpilot_version", "unknown"),
        system=data.get("system", {}),
        installed_apt_packages=data.get("installed_apt_packages", []),
        git_config=data.get("git_config", {}),
        environment_variables=data.get("environment_variables", {}),
        config_files=data.get("config_files", {}),
        devpilot_config=data.get("devpilot_config", {}),
    )


def load_snapshot(name_or_path: str) -> Snapshot:
    """Load a snapshot from its name or file path.

    If given a name (no .json extension), finds the most recent snapshot
    matching that name. If given a full path, loads that file directly.

    Args:
        name_or_path: Snapshot name or full path to a JSON file.

    Returns:
        The loaded Snapshot.

    Raises:
        FileNotFoundError: If no matching snapshot is found.
    """
    _ensure_dir()

    filepath = Path(name_or_path)
    if filepath.suffix == ".json" and filepath.exists():
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return _dict_to_snapshot(data)

    # Search by name prefix — return most recent
    safe_name = _sanitize_name(name_or_path)
    matches = sorted(
        SNAPSHOT_DIR.glob(f"{safe_name}_*.json"),
        reverse=True,
    )
    if not matches:
        raise FileNotFoundError(f"No snapshot found with name '{name_or_path}'")

    data = json.loads(matches[0].read_text(encoding="utf-8"))
    return _dict_to_snapshot(data)


def list_snapshots() -> list[Snapshot]:
    """List all saved snapshots, most recent first.

    Returns:
        List of Snapshot instances sorted by timestamp descending.
    """
    _ensure_dir()
    snapshots: list[Snapshot] = []
    for filepath in sorted(SNAPSHOT_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            snapshots.append(_dict_to_snapshot(data))
        except (json.JSONDecodeError, OSError):
            continue
    return snapshots
