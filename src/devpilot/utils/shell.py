"""Shell command helpers for DevPilot."""

import shutil
import subprocess
from pathlib import Path


def run_command(
    cmd: list[str],
    capture: bool = True,
    check: bool = False,
    timeout: int = 300,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a shell command safely using subprocess.run with list args (no shell=True).

    Args:
        cmd: Command and arguments as a list of strings.
        capture: Capture stdout/stderr if True.
        check: Raise CalledProcessError on non-zero exit if True.
        timeout: Command timeout in seconds.
        cwd: Working directory for the command.

    Returns:
        The completed process result.
    """
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
        timeout=timeout,
        cwd=str(cwd) if cwd else None,
    )


def which(program: str) -> Path | None:
    """Find a program in PATH.

    Args:
        program: Name of the executable.

    Returns:
        Path to the executable, or None if not found.
    """
    found = shutil.which(program)
    return Path(found) if found else None


def apt_install(packages: list[str]) -> bool:
    """Install packages via apt-get.

    Args:
        packages: List of package names to install.

    Returns:
        True if installation succeeded, False otherwise.
    """
    try:
        result = run_command(
            ["sudo", "apt-get", "install", "-y", *packages],
            capture=True,
            check=False,
            timeout=600,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return False
