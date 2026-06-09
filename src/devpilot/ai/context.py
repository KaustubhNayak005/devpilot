"""System context gathering for AI-powered diagnostics."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


def gather_context() -> dict[str, Any]:
    """Collect system context for AI prompts.

    Gathers OS release info, PATH, relevant environment variables,
    and installed apt packages. Each collection step is wrapped in
    try/except so a single failure does not crash the entire function.

    Returns:
        Dictionary with keys: os_release, path_entries, relevant_env,
        installed_packages.
    """
    try:
        os_release = _read_os_release()
    except Exception:
        os_release = {}

    try:
        path_entries = _get_path_entries()
    except Exception:
        path_entries = []

    try:
        relevant_env = _get_relevant_env()
    except Exception:
        relevant_env = {}

    try:
        installed_packages = _get_installed_packages()
    except Exception:
        installed_packages = []

    return {
        "os_release": os_release,
        "path_entries": path_entries,
        "relevant_env": relevant_env,
        "installed_packages": installed_packages,
    }


def _read_os_release() -> dict[str, str]:
    """Parse /etc/os-release into a dictionary.

    Returns:
        Dictionary of KEY=VALUE pairs, or empty dict on failure.
    """
    result: dict[str, str] = {}
    try:
        content = Path("/etc/os-release").read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                value = value.strip('"')
                result[key] = value
    except OSError:
        pass
    return result


def _get_path_entries() -> list[str]:
    """Get the PATH environment variable entries.

    Returns:
        List of directory paths from PATH, or empty list on failure.
    """
    try:
        return os.environ["PATH"].split(":")
    except KeyError:
        return []


def _get_relevant_env() -> dict[str, str]:
    """Collect a subset of environment variables relevant to development.

    Returns:
        Dictionary with only the keys that are set.
    """
    relevant_keys = ["JAVA_HOME", "GOPATH", "FLUTTER_HOME", "NVM_DIR"]
    result: dict[str, str] = {}
    for key in relevant_keys:
        try:
            value = os.environ[key]
            if value:
                result[key] = value
        except KeyError:
            pass
    return result


def _get_installed_packages() -> list[str]:
    """Run dpkg -l and parse the list of installed package names.

    Returns:
        List of package name strings, or empty list on failure.
    """
    try:
        proc = subprocess.run(
            ["dpkg", "-l"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        packages: list[str] = []
        for line in proc.stdout.splitlines():
            if line.startswith("ii"):
                parts = line.split()
                if len(parts) >= 2:
                    packages.append(parts[1])
        return packages
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return []
