"""DevPilot CLI — Typer entrypoint with info, doctor, setup, and init commands."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table

from devpilot.config.manager import ConfigManager
from devpilot.doctor.runner import run_all_doctors
from devpilot.logging.logger import setup_logger
from devpilot.modules.cpp.module import CppModule
from devpilot.modules.git.module import GitModule
from devpilot.modules.node.module import NodeModule
from devpilot.modules.nvim.module import NvimModule
from devpilot.modules.python.module import PythonModule
from devpilot.modules.vscode.module import VSCodeModule
from devpilot.utils.shell import run_command

app = typer.Typer(help="DevPilot — WSL2 developer workstation bootstrapper")
console = Console()
config = ConfigManager()

ALL_MODULES = {
    "git": GitModule,
    "python": PythonModule,
    "node": NodeModule,
    "cpp": CppModule,
    "vscode": VSCodeModule,
    "nvim": NvimModule,
}

INSTALL_ORDER = ["git", "python", "node", "cpp", "vscode", "nvim"]

logger = setup_logger()


def _get_system_info() -> dict[str, str]:
    """Collect WSL2 Ubuntu system information.

    Returns:
        Dictionary mapping property names to values.
    """
    info: dict[str, str] = {}

    try:
        result = run_command(["lsb_release", "-d"], capture=True, check=False)
        desc = result.stdout.split("Description:", 1)[-1] if result.stdout else ""
        info["Ubuntu"] = desc.strip() or "Unknown"
    except (OSError, FileNotFoundError):
        info["Ubuntu"] = "Unknown"

    try:
        result = run_command(["uname", "-r"], capture=True, check=False)
        info["Kernel"] = result.stdout.strip() if result.stdout else "Unknown"
    except (OSError, FileNotFoundError):
        info["Kernel"] = "Unknown"

    try:
        proc_version = Path("/proc/version").read_text(encoding="utf-8")
        if "icrosoft" in proc_version or "WSL" in proc_version:
            is_wsl2 = "4.4.0-" not in proc_version and "3.4" not in proc_version
            info["WSL Version"] = "WSL2" if is_wsl2 else "WSL1"
        else:
            info["WSL Version"] = "Not WSL"
    except OSError:
        info["WSL Version"] = "Unknown"

    try:
        result = run_command(["nproc"], capture=True, check=False)
        info["CPU Cores"] = result.stdout.strip() if result.stdout else "Unknown"
    except (OSError, FileNotFoundError):
        info["CPU Cores"] = "Unknown"

    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                kb = int(parts[1])
                gb = kb / (1024 * 1024)
                info["RAM"] = f"{gb:.1f} GB"
                break
    except OSError:
        info["RAM"] = "Unknown"

    try:
        result = run_command(["df", "-h", "/"], capture=True, check=False)
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            if len(parts) >= 4:
                info["Disk"] = (
                    f"{parts[1]} total, {parts[2]} used, " f"{parts[3]} available ({parts[4]})"
                )
            else:
                info["Disk"] = "Unknown"
        else:
            info["Disk"] = "Unknown"
    except (OSError, FileNotFoundError):
        info["Disk"] = "Unknown"

    return info


@app.command()
def info() -> None:
    """Display system information — Ubuntu, WSL version, CPU, RAM, disk."""
    sysinfo = _get_system_info()
    table = Table(title="[bold]DevPilot System Information[/bold]", show_header=False)
    table.add_column("Property", style="cyan", width=16)
    table.add_column("Value", style="green")
    for key, value in sysinfo.items():
        table.add_row(key, value)
    console.print(table)


@app.command()
def doctor(
    ai: Annotated[
        bool,
        typer.Option("--ai", help="Use AI to diagnose failures"),
    ] = False,
) -> None:
    """Run health checks across all modules and compute a health score."""
    if ai:
        from devpilot.ai.client import _get_api_key

        if not _get_api_key():
            console.print(
                Panel.fit(
                    "[yellow]AI features require OPENAI_API_KEY. "
                    "Set it in your environment or in ~/.config/devpilot/config.yaml[/yellow]",
                    border_style="yellow",
                )
            )
            sys.exit(0)

    modules = [cls() for cls in ALL_MODULES.values()]  # type: ignore[abstract]
    results, health_score = run_all_doctors(modules, ai_diagnose=ai)

    console.print(Panel.fit("[bold]DevPilot Doctor[/bold]", border_style="blue"))
    console.print()

    table = Table(title="Health Checks", show_header=True)
    table.add_column("Status", width=4)
    table.add_column("Check")
    table.add_column("Message", style="dim")
    table.add_column("Fix", style="yellow")

    for r in results:
        icon = "✅" if r.passed else "❌"
        table.add_row(icon, r.name, r.message, r.fix or "")

    console.print(table)
    console.print()

    if health_score >= 90:
        color = "green"
    elif health_score >= 60:
        color = "yellow"
    else:
        color = "red"

    console.print(
        Panel.fit(
            f"[bold {color}]Health Score: {health_score}/100[/bold {color}]",
            border_style=color,
        )
    )


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="Your question about your dev environment")],
) -> None:
    """Ask an AI expert a question about your WSL2 Ubuntu dev environment."""
    from devpilot.ai.client import _get_api_key
    from devpilot.ai.client import ask as ai_ask
    from devpilot.ai.context import gather_context

    if not _get_api_key():
        console.print(
            Panel.fit(
                "[yellow]AI features require OPENAI_API_KEY. "
                "Set it in your environment or in ~/.config/devpilot/config.yaml[/yellow]",
                border_style="yellow",
            )
        )
        sys.exit(0)

    console.print("[cyan]Gathering system context...[/cyan]")
    context = gather_context()
    console.print("[cyan]Thinking...[/cyan]")
    console.print()
    ai_ask(question, context)


@app.command()
def inspect(
    path: Annotated[
        str,
        typer.Argument(help="Path to project directory to inspect"),
    ] = ".",
) -> None:
    """Scan a project directory and detect what tools are needed."""
    from rich.prompt import Confirm

    from devpilot.inspector.checker import check_tools
    from devpilot.inspector.detector import detect_stack
    from devpilot.inspector.installer import MANUAL_INSTALL, install_missing

    root = Path(path).resolve()
    console.print(f"\n[bold]Scanning {root}...[/bold]\n")

    stacks = detect_stack(path)

    if not stacks:
        console.print("[yellow]No known project stacks detected.[/yellow]")
        return

    console.print("[bold]Detected stacks:[/bold]")
    for s in stacks:
        console.print(f"  [cyan]{s.name}[/cyan] (confidence: {s.confidence})")

    # Collect all unique tools
    all_tools: list[str] = []
    seen_tools: set[str] = set()
    for s in stacks:
        for tool in s.tools:
            if tool not in seen_tools:
                all_tools.append(tool)
                seen_tools.add(tool)

    console.print("\n[bold]Checking required tools:[/bold]")
    tool_status = check_tools(all_tools)

    table = Table(show_header=False)
    table.add_column("Tool", style="cyan")
    table.add_column("Status")
    for tool in all_tools:
        status = tool_status.get(tool, False)
        style = "green" if status else "red"
        label = "OK" if status else "MISSING"
        table.add_row(tool, f"[{style}]{label}[/{style}]")
    console.print(table)

    missing = [t for t in all_tools if not tool_status.get(t, False)]
    if not missing:
        console.print("\n[green]All tools are installed![/green]")
        return

    manual_tools = [t for t in missing if t in MANUAL_INSTALL]
    apt_tools = [t for t in missing if t not in MANUAL_INSTALL]

    if manual_tools:
        console.print("\n[yellow]Some tools require manual installation:[/yellow]")
        for t in manual_tools:
            console.print(f"  [yellow]{t}:[/yellow] {MANUAL_INSTALL[t]}")

    if not apt_tools:
        return

    if Confirm.ask(f"\nInstall {len(apt_tools)} missing tool(s)?"):
        for tool in apt_tools:
            console.print(f"\n[cyan]Installing {tool}...[/cyan]")
            success = install_missing(tool)
            if success:
                console.print(f"  [green]✓ {tool} installed[/green]")
            else:
                console.print(f"  [red]✗ {tool} failed[/red]")


snapshot_app = typer.Typer(help="Save and restore environment snapshots")
app.add_typer(snapshot_app, name="snapshot")


@snapshot_app.command("save")
def snapshot_save(
    name: Annotated[
        str,
        typer.Option("--name", help="Name for this snapshot"),
    ] = "",
) -> None:
    """Save the current environment state as a snapshot."""
    from devpilot.snapshot.capture import capture_snapshot
    from devpilot.snapshot.storage import save_snapshot

    snap_name = name if name else "auto"
    console.print(f"[cyan]Capturing snapshot as '{snap_name}'...[/cyan]")
    snapshot = capture_snapshot(snap_name)
    filepath = save_snapshot(snapshot)
    console.print(f"[green]✓ Snapshot saved to {filepath}[/green]")


@snapshot_app.command("list")
def snapshot_list() -> None:
    """List all saved snapshots."""
    from devpilot.snapshot.storage import list_snapshots

    snapshots = list_snapshots()
    if not snapshots:
        console.print("[yellow]No snapshots found.[/yellow]")
        return

    table = Table(title="[bold]Saved Snapshots[/bold]")
    table.add_column("Name", style="cyan")
    table.add_column("Timestamp", style="green")
    table.add_column("DevPilot Version", style="dim")

    for s in snapshots:
        table.add_row(s.name, s.timestamp, s.devpilot_version)

    console.print(table)


@snapshot_app.command("restore")
def snapshot_restore(
    name: Annotated[str, typer.Argument(help="Name of the snapshot to restore")],
) -> None:
    """Restore the environment from a snapshot."""
    from devpilot.snapshot.restore import restore_snapshot
    from devpilot.snapshot.storage import load_snapshot

    snapshot = load_snapshot(name)
    console.print(
        f"[bold]Restoring from snapshot: {snapshot.name} " f"({snapshot.timestamp})[/bold]"
    )
    restore_snapshot(snapshot)


@snapshot_app.command("diff")
def snapshot_diff(
    name: Annotated[str, typer.Argument(help="Name of the snapshot to diff against")],
) -> None:
    """Compare the current environment to a saved snapshot."""
    from devpilot.snapshot.capture import capture_snapshot
    from devpilot.snapshot.diff import diff_snapshots
    from devpilot.snapshot.storage import load_snapshot

    saved = load_snapshot(name)
    current = capture_snapshot("__current__")

    diff = diff_snapshots(saved, current)

    console.print(f"\n[bold]Snapshot: {saved.name} ({saved.timestamp})[/bold]\n")

    if diff.added_packages:
        console.print(f"[green]Packages added since snapshot ({len(diff.added_packages)}):[/green]")
        for pkg in diff.added_packages:
            console.print(f"  [green]{pkg}[/green]")
        console.print()

    if diff.removed_packages:
        console.print(f"[red]Packages removed since snapshot ({len(diff.removed_packages)}):[/red]")
        for pkg in diff.removed_packages:
            console.print(f"  [red]{pkg}[/red]")
        console.print()

    if diff.changed_env_vars:
        console.print("[yellow]Environment changes:[/yellow]")
        for key, (old, new) in diff.changed_env_vars.items():
            old_display = old or "not set"
            new_display = new or "not set"
            console.print(f"  [yellow]{key}:[/yellow] {old_display} → {new_display}")
        console.print()

    if diff.changed_config_files:
        console.print("[yellow]Config file changes:[/yellow]")
        for f in diff.changed_config_files:
            console.print(f"  [yellow]{f}[/yellow]")
        console.print()

    if not any(
        [
            diff.added_packages,
            diff.removed_packages,
            diff.changed_env_vars,
            diff.changed_config_files,
        ]
    ):
        console.print("[green]No differences — snapshot matches current environment.[/green]")


@app.command()
def setup(
    module_name: Annotated[
        str | None,
        typer.Argument(help="Optional: install a single module by name"),
    ] = None,
) -> None:
    """Install development tools. Run without arguments to install everything."""
    if module_name:
        if module_name not in ALL_MODULES:
            console.print(f"[red]Unknown module: {module_name}[/red]")
            available = ", ".join(sorted(ALL_MODULES))
            console.print(f"Available modules: {available}")
            raise typer.Exit(code=1)
        target_modules = [module_name]
    else:
        target_modules = INSTALL_ORDER

    config_mgr = ConfigManager()
    failed: list[str] = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("✓"),
        console=console,
    ) as progress:
        task = progress.add_task("Installing", total=len(target_modules))

        for name in target_modules:
            progress.update(task, description=f"[cyan]Setting up {name}...")

            try:
                module = ALL_MODULES[name]()  # type: ignore[abstract]
                success = module.install()
                if success:
                    config_mgr.mark_installed(name)
                else:
                    failed.append(name)
                    console.print(f"[yellow]⚠ {name} setup completed with warnings[/yellow]")
            except Exception as exc:
                failed.append(name)
                logger.exception(f"Module {name} raised an exception during install.")
                console.print(f"[red]✗ {name} failed: {exc}[/red]")

            progress.advance(task)

    console.print()
    if failed:
        console.print(f"[yellow]Completed with issues in: {', '.join(failed)}[/yellow]")
    else:
        console.print("[green]All modules installed successfully![/green]")


@app.command()
def init(
    template: Annotated[str, typer.Argument(help="Template: cpp, python, or cli")],
    project_name: Annotated[str, typer.Argument(help="Name for the new project")],
) -> None:
    """Scaffold a new project from a template."""
    allowed = {"cpp", "python", "cli"}
    if template not in allowed:
        console.print(f"[red]Unknown template: {template}[/red]")
        console.print(f"Available templates: {', '.join(sorted(allowed))}")
        raise typer.Exit(code=1)

    project_dir = Path.cwd() / project_name
    if project_dir.exists():
        console.print(f"[red]Directory already exists: {project_dir}[/red]")
        raise typer.Exit(code=1)

    project_dir.mkdir(parents=True)

    if template == "cpp":
        _scaffold_cpp(project_dir, project_name)
    elif template == "python":
        _scaffold_python(project_dir, project_name, cli=False)
    elif template == "cli":
        _scaffold_python(project_dir, project_name, cli=True)

    console.print(
        f"[green]✓[/green] Scaffolded [bold]{template}[/bold] "
        f"project in [bold]{project_dir}[/bold]"
    )


def _scaffold_cpp(root: Path, project_name: str) -> None:
    """Create a C++ project with CMake structure."""
    (root / "CMakeLists.txt").write_text(
        f"""cmake_minimum_required(VERSION 3.16)
project({project_name} VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable({project_name} src/main.cpp)
""",
        encoding="utf-8",
    )

    src_dir = root / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "main.cpp").write_text(
        f"""#include <iostream>

int main() {{
    std::cout << "Hello from {project_name}!" << std::endl;
    return 0;
}}
""",
        encoding="utf-8",
    )

    (root / ".gitignore").write_text(
        "build/\n*.out\n*.o\n.cache/\n",
        encoding="utf-8",
    )


def _scaffold_python(root: Path, project_name: str, cli: bool) -> None:
    """Create a Python project with pyproject.toml and src layout."""
    python_dir = root / "src" / project_name
    python_dir.mkdir(parents=True, exist_ok=True)
    (python_dir / "__init__.py").write_text(
        f'"""Source package for {project_name}."""\n', encoding="utf-8"
    )

    if cli:
        main_code = f'''"""CLI entrypoint for {project_name}."""

import typer

app = typer.Typer(help="{project_name} — a CLI tool.")


@app.command()
def hello() -> None:
    """Print a greeting."""
    typer.echo("Hello from {project_name}!")


if __name__ == "__main__":
    app()
'''
    else:
        main_code = f'''"""Main module for {project_name}."""


def main() -> None:
    """Entrypoint for {project_name}."""
    print("Hello from {project_name}!")


if __name__ == "__main__":
    main()
'''

    (python_dir / "main.py").write_text(main_code, encoding="utf-8")

    tests_dir = root / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "test_main.py").write_text(
        f"""from {project_name}.main import main


def test_main_runs() -> None:
    main()
""",
        encoding="utf-8",
    )

    pyproject = f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{project_name}"
version = "0.1.0"
description = ""
readme = "README.md"
requires-python = ">=3.12"
"""
    if cli:
        pyproject += f"""
dependencies = ["typer[all]>=0.15"]

[project.scripts]
{project_name} = "{project_name}.main:app"
"""
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")

    (root / "README.md").write_text(f"# {project_name}\n", encoding="utf-8")
    (root / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.venv/\ndist/\n*.egg-info/\n",
        encoding="utf-8",
    )
