"""Snapshot restoration — installs missing packages and restores config files."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from devpilot.snapshot.capture import CONFIG_FILES_TO_HASH, Snapshot, _capture_apt_packages
from devpilot.utils.shell import run_command

console = Console()


def _current_packages() -> list[str]:
    """Get the currently installed apt packages.

    Returns:
        List of package names.
    """
    return _capture_apt_packages()


def restore_snapshot(snapshot: Snapshot) -> None:
    """Interactively restore the environment from a snapshot.

    Installs missing apt packages and prompts about config files
    whose hashes have changed. Never auto-overwrites config files.

    Args:
        snapshot: The snapshot to restore from.
    """
    # Restore apt packages
    current_pkgs = set(_current_packages())
    snapshot_pkgs = set(snapshot.installed_apt_packages)
    missing_pkgs = sorted(snapshot_pkgs - current_pkgs)

    if missing_pkgs:
        console.print(f"\n[bold yellow]{len(missing_pkgs)} package(s) missing:[/bold yellow]")
        for pkg in missing_pkgs:
            console.print(f"  [yellow]{pkg}[/yellow]")

        if Confirm.ask("Install missing packages?"):
            try:
                result = run_command(
                    ["sudo", "apt-get", "install", "-y", *missing_pkgs],
                    capture=True,
                    check=False,
                    timeout=300,
                )
                if result.returncode == 0:
                    console.print(f"[green]✓ Installed {len(missing_pkgs)} package(s)[/green]")
                else:
                    console.print("[red]Package installation failed. Check the output above.[/red]")
            except (OSError, FileNotFoundError):
                console.print("[red]Package installation failed.[/red]")
    else:
        console.print("[green]✓ All packages are already installed[/green]")

    # Check config files
    from devpilot.snapshot.capture import _capture_config_file_hashes

    current_hashes = _capture_config_file_hashes()
    changed_files: list[str] = []

    for file_path in CONFIG_FILES_TO_HASH:
        saved_hash = snapshot.config_files.get(file_path)
        current_hash = current_hashes.get(file_path)

        if saved_hash is None:
            # File didn't exist at snapshot time
            if current_hash is not None:
                console.print(
                    f"[yellow]Config file present now but not in snapshot: {file_path}[/yellow]"
                )
            continue

        if current_hash is None:
            console.print(
                f"[yellow]Config file was in snapshot but missing now: {file_path}[/yellow]"
            )
            continue

        if saved_hash != current_hash:
            changed_files.append(file_path)

    if changed_files:
        console.print("\n[yellow]Config files that have changed:[/yellow]")
        for f in changed_files:
            console.print(f"  [yellow]{f}[/yellow]")

        for f in changed_files:
            full_path = Path(f).expanduser()
            if full_path.exists():
                if Confirm.ask(f"{f} has changed. Restore from snapshot?"):
                    console.print(
                        "[yellow]Manual restoration required. "
                        "Snapshot only stores hashes, not content.[/yellow]"
                    )
    else:
        console.print("[green]✓ Config files match the snapshot[/green]")

    # Environment variables — warning only
    if snapshot.environment_variables:
        console.print(
            "\n[yellow]Environment variables from snapshot "
            "(cannot be restored to your current shell):[/yellow]"
        )
        for key, value in snapshot.environment_variables.items():
            console.print(f"  [dim]{key}={value}[/dim]")
