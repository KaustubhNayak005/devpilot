"""Environment snapshot capture — records system state for later comparison."""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from devpilot.config.manager import ConfigManager
from devpilot.utils.shell import run_command

CONFIG_FILES_TO_HASH: list[str] = [
    "~/.gitconfig",
    "~/.zshrc",
    "~/.bashrc",
    "~/.profile",
    "~/.config/nvim/init.lua",
]

# Config files larger than this are hashed but their contents are not stored.
MAX_CONFIG_CONTENT_BYTES: int = 256 * 1024

ENV_VARS_TO_CAPTURE: list[str] = [
    "PATH",
    "SHELL",
    "EDITOR",
    "JAVA_HOME",
    "GOPATH",
    "FLUTTER_HOME",
    "NVM_DIR",
    "PYENV_ROOT",
]


@dataclass
class Snapshot:
    """A point-in-time record of the development environment.

    Attributes:
        name: Human-readable snapshot name.
        timestamp: ISO 8601 timestamp of when the snapshot was taken.
        devpilot_version: Version of DevPilot used to create the snapshot.
        system: OS release, hostname, and WSL version info.
        installed_apt_packages: List of installed apt package names.
        git_config: Git global configuration key-value pairs.
        environment_variables: A subset of relevant environment variables.
        config_files: Mapping of config file path -> SHA-256 hash.
        devpilot_config: Contents of the DevPilot config file.
        config_file_contents: Mapping of config file path -> full text content
            (only for small UTF-8 files; enables real restoration).
    """

    name: str
    timestamp: str
    devpilot_version: str
    system: dict[str, str]
    installed_apt_packages: list[str]
    git_config: dict[str, str]
    environment_variables: dict[str, str]
    config_files: dict[str, str]
    devpilot_config: dict[str, Any]
    config_file_contents: dict[str, str] = field(default_factory=dict)


def _capture_system() -> dict[str, str]:
    """Collect OS release, hostname, and WSL version information.

    Returns:
        Dictionary with keys like os_release, hostname, wsl_version.
        May contain 'error' key if collection fails entirely.
    """
    info: dict[str, str] = {}
    try:
        result = run_command(["hostname"], capture=True, check=False)
        info["hostname"] = result.stdout.strip() if result.stdout else "unknown"
    except (OSError, FileNotFoundError):
        info["hostname"] = "unknown"

    try:
        content = Path("/etc/os-release").read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                value = value.strip('"')
                info[f"os_{key.lower()}"] = value
    except OSError:
        pass

    try:
        proc_version = Path("/proc/version").read_text(encoding="utf-8")
        if "icrosoft" in proc_version or "WSL" in proc_version:
            is_wsl2 = "4.4.0-" not in proc_version and "3.4" not in proc_version
            info["wsl_version"] = "WSL2" if is_wsl2 else "WSL1"
        else:
            info["wsl_version"] = "Not WSL"
    except OSError:
        info["wsl_version"] = "unknown"

    return info


def _capture_apt_packages() -> list[str]:
    """Get the list of installed apt packages.

    Returns:
        List of package names, or empty list on failure.
    """
    try:
        result = run_command(
            ["dpkg", "--get-selections"],
            capture=True,
            check=False,
            timeout=30,
        )
        packages: list[str] = []
        for line in result.stdout.splitlines():
            if "\tinstall" in line:
                packages.append(line.split("\t")[0])
        return packages
    except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _capture_git_config() -> dict[str, str]:
    """Read global git configuration.

    Returns:
        Dictionary of git config keys to values, or empty dict on failure.
    """
    try:
        result = run_command(
            ["git", "config", "--global", "--list"],
            capture=True,
            check=False,
            timeout=10,
        )
        config: dict[str, str] = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if "=" in line:
                key, _, value = line.partition("=")
                config[key] = value
        return config
    except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
        return {}


def _capture_env_vars() -> dict[str, str]:
    """Capture a subset of relevant environment variables.

    Returns:
        Dictionary of only the ENV_VARS_TO_CAPTURE keys that are set.
    """
    result: dict[str, str] = {}
    for key in ENV_VARS_TO_CAPTURE:
        try:
            value = os.environ[key]
            if value:
                result[key] = value
        except KeyError:
            pass
    return result


def _capture_config_file_hashes() -> dict[str, str]:
    """Hash config files without storing their contents.

    Returns:
        Dictionary mapping file path to SHA-256 hex digest.
        Missing or unreadable files are omitted.
    """
    hashes: dict[str, str] = {}
    for file_path in CONFIG_FILES_TO_HASH:
        expanded = Path(file_path).expanduser()
        try:
            content = expanded.read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            hashes[file_path] = sha
        except OSError:
            pass
    return hashes


def _capture_config_file_contents() -> dict[str, str]:
    """Store the text contents of small config files so restore can rewrite them.

    Files larger than MAX_CONFIG_CONTENT_BYTES or not valid UTF-8 are skipped —
    those remain hash-only, as in snapshot format v1.

    Returns:
        Dictionary mapping file path to full text content.
    """
    contents: dict[str, str] = {}
    for file_path in CONFIG_FILES_TO_HASH:
        expanded = Path(file_path).expanduser()
        try:
            raw = expanded.read_bytes()
        except OSError:
            continue
        if len(raw) > MAX_CONFIG_CONTENT_BYTES:
            continue
        try:
            contents[file_path] = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
    return contents


def _capture_devpilot_config() -> dict[str, Any]:
    """Read the current DevPilot configuration.

    Returns:
        The loaded config dictionary, or empty dict on failure.
    """
    try:
        manager = ConfigManager()
        return manager.load()
    except Exception:
        return {}


def _get_devpilot_version() -> str:
    """Get the installed DevPilot version.

    Returns:
        Version string, or 'unknown' if it can't be determined.
    """
    try:
        from importlib.metadata import version

        return version("devpilot")
    except Exception:
        return "unknown"


def capture_snapshot(name: str) -> Snapshot:
    """Capture the current environment state into a Snapshot.

    Each capture step is wrapped in try/except — if a step fails,
    that field is stored as empty or null. The function never raises.

    Args:
        name: Human-readable name for the snapshot.

    Returns:
        A Snapshot containing the captured state.
    """
    return Snapshot(
        name=name,
        timestamp=datetime.now(UTC).isoformat(),
        devpilot_version=_get_devpilot_version(),
        system=_capture_system(),
        installed_apt_packages=_capture_apt_packages(),
        git_config=_capture_git_config(),
        environment_variables=_capture_env_vars(),
        config_files=_capture_config_file_hashes(),
        devpilot_config=_capture_devpilot_config(),
        config_file_contents=_capture_config_file_contents(),
    )
