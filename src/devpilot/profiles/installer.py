"""Profile installer — runs apt, pip, npm for a developer profile."""

from __future__ import annotations

import subprocess

from rich.console import Console
from rich.panel import Panel

from devpilot.profiles import Profile

console = Console()


def install_profile(profile: Profile, dry_run: bool = False) -> bool:
    """Install all tools for a developer profile.

    1. Installs apt packages (requires sudo).
    2. Installs pip packages (user-scoped).
    3. Installs global npm packages.
    4. Prints post-install notes.

    Args:
        profile: The Profile to install.
        dry_run: If True, only print what would be done without executing.

    Returns:
        True if all steps succeeded (or if dry_run), False if any step failed.
    """
    if dry_run:
        console.print(f"[bold]Dry run for profile: {profile.name}[/bold]")
        if profile.apt_packages:
            console.print(f"  apt: {' '.join(profile.apt_packages)}")
        if profile.pip_packages:
            console.print(f"  pip: {' '.join(profile.pip_packages)}")
        if profile.npm_packages:
            console.print(f"  npm: {' '.join(profile.npm_packages)}")
        if profile.post_install_notes:
            console.print("  Notes:")
            for note in profile.post_install_notes:
                console.print(f"    - {note}")
        return True

    success = True

    # 1. apt packages
    if profile.apt_packages:
        console.print("[bold]Installing apt packages...[/bold]")
        try:
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y"] + profile.apt_packages,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                console.print("[green]apt packages installed.[/green]")
            else:
                console.print(f"[red]apt install failed: {result.stderr.strip()}[/red]")
                success = False
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError) as exc:
            console.print(f"[red]apt install error: {exc}[/red]")
            success = False

    # 2. pip packages
    if profile.pip_packages:
        console.print("[bold]Installing pip packages...[/bold]")
        try:
            result = subprocess.run(
                ["pip", "install"] + profile.pip_packages,
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode == 0:
                console.print("[green]pip packages installed.[/green]")
            else:
                console.print(f"[red]pip install failed: {result.stderr.strip()}[/red]")
                success = False
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError) as exc:
            console.print(f"[red]pip install error: {exc}[/red]")
            success = False

    # 3. npm packages
    if profile.npm_packages:
        console.print("[bold]Installing npm global packages...[/bold]")
        try:
            result = subprocess.run(
                ["npm", "install", "-g"] + profile.npm_packages,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                console.print("[green]npm packages installed.[/green]")
            else:
                console.print(f"[red]npm install failed: {result.stderr.strip()}[/red]")
                success = False
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError) as exc:
            console.print(f"[red]npm install error: {exc}[/red]")
            success = False

    # 4. Post-install notes
    if profile.post_install_notes:
        console.print()
        for note in profile.post_install_notes:
            console.print(Panel.fit(f"[bold]Note:[/bold] {note}", border_style="blue"))

    return success
