"""Known fixes for module health check failures — offline, no LLM needed."""

from __future__ import annotations

import logging
from typing import Callable

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


def fix_ccpp(logger: logging.Logger) -> bool:
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


def fix_vscode(logger: logging.Logger) -> bool:
    """Cannot auto-fix VSCode — print instructions."""
    logger.info("VSCode must be installed on the Windows host, not inside WSL.")
    logger.info("Download from: https://code.visualstudio.com/")
    return False


def fix_neovim(logger: logging.Logger) -> bool:
    """Re-install neovim if missing."""
    result = run_command(["sudo", "apt-get", "install", "-y", "neovim"])
    return result.returncode == 0


FIXES: dict[str, Callable[[logging.Logger], bool]] = {
    "git": fix_git,
    "python": fix_python,
    "node": fix_node,
    "ccpp": fix_ccpp,
    "vscode": fix_vscode,
    "neovim": fix_neovim,
}
