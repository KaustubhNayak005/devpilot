"""Known fixes for module health check failures — offline, no LLM needed."""

from __future__ import annotations

import logging
from collections.abc import Callable

from devpilot.utils.shell import run_command


def fix_git(logger: logging.Logger) -> bool:
    """Re-install git if missing."""
    result = run_command(["sudo", "apt-get", "install", "-y", "git"])
    return result.returncode == 0


def fix_python(logger: logging.Logger) -> bool:
    """Re-install python3 and pip if missing."""
    result = run_command(["sudo", "apt-get", "install", "-y", "python3", "python3-pip"])
    return result.returncode == 0


def fix_node(logger: logging.Logger) -> bool:
    """Re-install nodejs if missing."""
    result = run_command(["sudo", "apt-get", "install", "-y", "nodejs", "npm"])
    return result.returncode == 0


def fix_cpp(logger: logging.Logger) -> bool:
    """Re-install gcc and build tools if missing."""
    result = run_command(
        [
            "sudo",
            "apt-get",
            "install",
            "-y",
            "gcc",
            "g++",
            "make",
            "cmake",
            "build-essential",
        ]
    )
    return result.returncode == 0


def fix_docker(logger: logging.Logger) -> bool:
    """Re-install docker.io and start the service if missing."""
    result = run_command(["sudo", "apt-get", "install", "-y", "docker.io"])
    if result.returncode != 0:
        return False
    run_command(["sudo", "service", "docker", "start"])
    return True


def fix_vscode(logger: logging.Logger) -> bool:
    """Cannot auto-fix VSCode — print instructions."""
    logger.info("VSCode must be installed on the Windows host, not inside WSL.")
    logger.info("Download from: https://code.visualstudio.com/")
    return False


def fix_nvim(logger: logging.Logger) -> bool:
    """Re-install neovim if missing."""
    result = run_command(["sudo", "apt-get", "install", "-y", "neovim"])
    return result.returncode == 0


# Keys MUST match BaseModule.name values registered in the CLI's ALL_MODULES,
# otherwise `doctor --fix` silently skips the module.
FIXES: dict[str, Callable[[logging.Logger], bool]] = {
    "git": fix_git,
    "python": fix_python,
    "node": fix_node,
    "cpp": fix_cpp,
    "docker": fix_docker,
    "vscode": fix_vscode,
    "nvim": fix_nvim,
}
