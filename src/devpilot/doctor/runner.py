"""Doctor runner — aggregates health checks across all modules."""

from devpilot.modules.base import BaseModule, CheckResult


def run_all_doctors(modules: list[BaseModule]) -> tuple[list[CheckResult], int]:
    """Run doctor() on every module and compute the overall health score.

    Args:
        modules: A list of BaseModule instances to run doctor() against.

    Returns:
        A tuple of (all_results, health_score). health_score is an integer
        from 0 to 100 representing the percentage of passing checks.
    """
    all_results: list[CheckResult] = []
    for module in modules:
        all_results.extend(module.doctor())

    total = len(all_results)
    passed = sum(1 for r in all_results if r.passed)

    health_score = round((passed / total) * 100) if total > 0 else 100
    return all_results, health_score
