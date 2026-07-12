"""Snapshot restoration — installs missing packages and restores config files."""

from __future__ import annotations

import shutil
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


def _restore_config_file(snapshot: Snapshot, file_path: str) -> None:
    """Offer to restore a single config file from the snapshot's stored content.

    The current file (if any) is backed up to <name>.devpilot.bak before
    being overwritten. Snapshots created before content capture existed
    only store hashes — those fall back to a manual-restoration notice.

    Args:
        snapshot: The snapshot being restored.
        file_path: The config file path (with ~) to restore.
    """
    saved_content = snapshot.config_file_contents.get(file_path)
    full_path = Path(file_path).expanduser()
    state = "changed" if full_path.exists() else "missing"

    if saved_content is None:
        console.print(
            f"[yellow]{file_path} is {state}, but this snapshot only stores its hash "
            "(pre-v0.3 snapshot). Manual restoration required.[/yellow]"
        )
        return

    if not Confirm.ask(f"{file_path} is {state}. Restore it from the snapshot?"):
        return

    if full_path.exists():
        backup = full_path.with_name(full_path.name + ".devpilot.bak")
        shutil.copy2(full_path, backup)
        console.print(f"  [dim]Current file backed up to {backup}[/dim]")

    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(saved_content, encoding="utf-8")
    console.print(f"  [green]✓ Restored {file_path}[/green]")


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
                    timeout=1800,
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
    files_to_restore: list[str] = []

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

        if saved_hash != current_hash:
            files_to_restore.append(file_path)

    if files_to_restore:
        console.print("\n[yellow]Config files that differ from the snapshot:[/yellow]")
        for f in files_to_restore:
            console.print(f"  [yellow]{f}[/yellow]")
        for f in files_to_restore:
            _restore_config_file(snapshot, f)
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
