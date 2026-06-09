"""Snapshot diffing — compare a saved snapshot to the current environment."""

from __future__ import annotations

from dataclasses import dataclass, field

from devpilot.snapshot.capture import Snapshot


@dataclass
class SnapshotDiff:
    """Differences between a saved snapshot and the current environment.

    Attributes:
        added_packages: Packages installed now that weren't in the snapshot.
        removed_packages: Packages in the snapshot that are no longer installed.
        changed_env_vars: Environment variable changes (key -> (old, new)).
        changed_config_files: Config files whose hashes differ.
    """

    added_packages: list[str] = field(default_factory=list)
    removed_packages: list[str] = field(default_factory=list)
    changed_env_vars: dict[str, tuple[str | None, str | None]] = field(default_factory=dict)
    changed_config_files: list[str] = field(default_factory=list)


def diff_snapshots(saved: Snapshot, current: Snapshot) -> SnapshotDiff:
    """Compare a saved snapshot to the current environment.

    Args:
        saved: The snapshot to compare against.
        current: A freshly-captured snapshot of the current state.

    Returns:
        A SnapshotDiff summarizing all differences.
    """
    diff = SnapshotDiff()

    # Package differences
    saved_pkgs = set(saved.installed_apt_packages)
    current_pkgs = set(current.installed_apt_packages)
    diff.added_packages = sorted(current_pkgs - saved_pkgs)
    diff.removed_packages = sorted(saved_pkgs - current_pkgs)

    # Environment variable differences
    all_keys = set(
        list(saved.environment_variables.keys()) + list(current.environment_variables.keys())
    )
    for key in all_keys:
        old_val = saved.environment_variables.get(key)
        new_val = current.environment_variables.get(key)
        if old_val != new_val:
            diff.changed_env_vars[key] = (old_val, new_val)

    # Config file hash differences
    for file_path in set(list(saved.config_files.keys()) + list(current.config_files.keys())):
        old_hash = saved.config_files.get(file_path)
        new_hash = current.config_files.get(file_path)
        if old_hash != new_hash:
            diff.changed_config_files.append(file_path)
    diff.changed_config_files.sort()

    return diff
