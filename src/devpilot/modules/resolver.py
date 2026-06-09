"""Topological sort for module installation order."""

from __future__ import annotations

from collections import deque

from devpilot.modules.base import BaseModule


def resolve_install_order(modules: dict[str, BaseModule]) -> list[str]:
    """Return module names in dependency-safe install order using Kahn's algorithm.

    Args:
        modules: dict mapping module name to module instance.

    Returns:
        List of module names in safe install order.

    Raises:
        ValueError: if a circular dependency is detected.
    """
    in_degree: dict[str, int] = {name: 0 for name in modules}
    dependents: dict[str, list[str]] = {name: [] for name in modules}

    for name, module in modules.items():
        for dep in module.dependencies:
            if dep not in modules:
                continue
            in_degree[name] += 1
            dependents[dep].append(name)

    queue: deque[str] = deque(name for name, degree in in_degree.items() if degree == 0)
    result: list[str] = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for dependent in dependents[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(result) != len(modules):
        cycle = [n for n in modules if n not in result]
        raise ValueError(f"Circular dependency detected among: {cycle}")

    return result
