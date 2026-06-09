"""Tool installer for project inspection — installs missing tools."""

from __future__ import annotations

from devpilot.utils.shell import run_command

INSTALL_COMMANDS: dict[str, list[str]] = {
    "cmake": ["sudo", "apt-get", "install", "-y", "cmake"],
    "ninja-build": ["sudo", "apt-get", "install", "-y", "ninja-build"],
    "clangd": ["sudo", "apt-get", "install", "-y", "clangd"],
    "gcc": ["sudo", "apt-get", "install", "-y", "gcc"],
    "golang": ["sudo", "apt-get", "install", "-y", "golang"],
    "nodejs": ["sudo", "apt-get", "install", "-y", "nodejs"],
    "npm": ["sudo", "apt-get", "install", "-y", "npm"],
    "docker": ["sudo", "apt-get", "install", "-y", "docker.io"],
    "docker-compose": ["sudo", "apt-get", "install", "-y", "docker-compose"],
    "gh": ["sudo", "apt-get", "install", "-y", "gh"],
    "python3": ["sudo", "apt-get", "install", "-y", "python3"],
    "pip": ["sudo", "apt-get", "install", "-y", "python3-pip"],
    "rustup": [
        "curl",
        "--proto",
        "=https",
        "--tlsv1.2",
        "-sSf",
        "https://sh.rustup.rs",
    ],
}

MANUAL_INSTALL: dict[str, str] = {
    "flutter": "Install Flutter: https://docs.flutter.dev/get-started/install/linux",
    "dart": "Dart comes with Flutter. Install Flutter first.",
    "android-sdk": "Install Android Studio: https://developer.android.com/studio",
    "java-17": "Run: sudo apt-get install -y openjdk-17-jdk",
}


def install_missing(tool: str) -> bool:
    """Install a missing tool.

    Uses apt-get for most tools. Complex tools like Flutter are marked as
    manual — their instructions are printed instead of executed.

    Args:
        tool: The tool name to install.

    Returns:
        True if installation succeeded (or was not needed), False on failure.
    """
    if tool in MANUAL_INSTALL:
        return False

    cmd = INSTALL_COMMANDS.get(tool)
    if cmd is None:
        return False

    try:
        result = run_command(cmd, capture=True, check=False, timeout=120)
        return result.returncode == 0
    except (OSError, FileNotFoundError):
        return False
