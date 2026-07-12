"""Doctor runner — aggregates health checks across all modules."""

from __future__ import annotations

import shlex
import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from devpilot.modules.base import BaseModule, CheckResult

console = Console()


def run_all_doctors(
    modules: list[BaseModule],
    ai_diagnose: bool = False,
    fix: bool = False,
) -> tuple[list[CheckResult], int]:
    """Run doctor() on every module and compute the overall health score.

    Args:
        modules: A list of BaseModule instances to run doctor() against.
        ai_diagnose: If True, send failures to AI for diagnosis and offer fixes.
        fix: If True, run known fixes automatically for failing modules before
             falling through to AI diagnosis (if also enabled).

    Returns:
        A tuple of (all_results, health_score). health_score is an integer
        from 0 to 100 representing the percentage of passing checks.
    """
    all_results, module_results = _collect_results(modules)

    if fix and any(not r.passed for r in all_results):
        _run_fixes(modules, module_results)
        # Re-run doctors so the reported results and score reflect post-fix state.
        all_results, module_results = _collect_results(modules)

    total = len(all_results)
    passed = sum(1 for r in all_results if r.passed)
    health_score = round((passed / total) * 100) if total > 0 else 100

    if ai_diagnose:
        _run_ai_diagnosis(modules, module_results)

    return all_results, health_score


def _collect_results(
    modules: list[BaseModule],
) -> tuple[list[CheckResult], dict[str, list[CheckResult]]]:
    """Run doctor() on every module and collect the results."""
    all_results: list[CheckResult] = []
    module_results: dict[str, list[CheckResult]] = {}
    for module in modules:
        results = module.doctor()
        all_results.extend(results)
        module_results[module.name] = results
    return all_results, module_results


def _run_fixes(
    modules: list[BaseModule],
    module_results: dict[str, list[CheckResult]],
) -> None:
    """Run known fixes for failing modules — offline, no LLM needed.

    Args:
        modules: List of BaseModule instances.
        module_results: Mapping of module name to its list of CheckResults.
    """
    from devpilot.doctor.fixes import FIXES

    console.print()
    console.print(Panel.fit("[bold yellow]Auto-Fix Mode[/bold yellow]", border_style="yellow"))
    console.print()

    module_map: dict[str, BaseModule] = {m.name: m for m in modules}

    for module_name, results in module_results.items():
        all_pass = all(r.passed for r in results)
        if all_pass:
            continue

        fix_func = FIXES.get(module_name)
        if fix_func is None:
            console.print(f"[yellow]{module_name}:[/yellow] No fix available — skip.")
            continue

        console.print(f"[bold]{module_name}:[/bold] FAIL → running fix...")
        try:
            import logging

            logger = logging.getLogger("devpilot.doctor")
            success = fix_func(logger)
        except Exception as exc:
            console.print(f"  [red]Fix raised exception: {exc}[/red]")
            success = False

        module = module_map.get(module_name)
        if module:
            verify_results = module.verify()
            all_fixed = all(r.passed for r in verify_results)
            if all_fixed and success is not False:
                console.print("  [green]Fixed successfully[/green]")
            elif not success:
                console.print("  [red]Fix failed — manual action required[/red]")
            else:
                console.print("  [yellow]Fix ran but checks still failing[/yellow]")
        else:
            console.print("  [yellow]Could not re-verify[/yellow]")

    console.print()


def _run_ai_diagnosis(
    modules: list[BaseModule],
    module_results: dict[str, list[CheckResult]],
) -> None:
    """Run AI-powered diagnosis on failed health checks.

    Args:
        modules: List of BaseModule instances.
        module_results: Mapping of module name to its list of CheckResults.
    """
    from devpilot.ai.client import diagnose
    from devpilot.ai.context import gather_context

    failures: list[dict[str, str]] = []
    module_map: dict[str, BaseModule] = {m.name: m for m in modules}

    for module_name, results in module_results.items():
        for r in results:
            if not r.passed:
                failures.append(
                    {
                        "module": module_name,
                        "check_name": r.name,
                        "message": r.message,
                    }
                )

    if not failures:
        return

    console.print()
    console.print(Panel.fit("[bold blue]AI-Powered Diagnosis[/bold blue]", border_style="blue"))
    console.print()

    context = gather_context()
    diagnoses = diagnose(failures, context)

    if not diagnoses:
        console.print("[yellow]AI could not generate any diagnoses.[/yellow]")
        return

    for d in diagnoses:
        fix_color = "green" if d.suggested_fix else "yellow"
        fix_text = d.suggested_fix or "No safe auto-fix available"

        panel_content = (
            f"[bold]Module:[/bold] {d.module_name}\n"
            f"[bold]Root Cause:[/bold] {d.root_cause}\n"
            f"[bold]Explanation:[/bold] {d.explanation}\n"
            f"[bold]Suggested Fix:[/bold] [{fix_color}]{fix_text}[/{fix_color}]"
        )
        console.print(Panel.fit(panel_content, border_style="blue"))
        console.print()

        if d.suggested_fix:
            run_fix = Confirm.ask("Run this fix?", default=True)
            if run_fix:
                try:
                    cmd_parts = shlex.split(d.suggested_fix)
                    result = subprocess.run(
                        cmd_parts,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode == 0:
                        console.print("[green]Fix applied successfully![/green]")
                    else:
                        console.print(f"[red]Fix failed (exit code {result.returncode}).[/red]")
                        if result.stderr:
                            console.print(f"[red]Error: {result.stderr.strip()}[/red]")
                except (subprocess.TimeoutExpired, OSError, FileNotFoundError) as exc:
                    console.print(f"[red]Fix execution error: {exc}[/red]")

                module = module_map.get(d.module_name)
                if module:
                    console.print(f"\n[bold]Re-checking {d.module_name}...[/bold]")
                    verify_results = module.verify()
                    for vr in verify_results:
                        icon = "✅" if vr.passed else "❌"
                        console.print(f"  {icon} {vr.name}: {vr.message}")
                console.print()
