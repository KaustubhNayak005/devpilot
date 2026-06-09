# DevPilot — Full Implementation Plan

## Architecture Overview

DevPilot is a pipx-installable Typer CLI that bootstraps WSL2 Ubuntu dev environments. Six modules (git, python, node, cpp, vscode, nvim) implement a common ABC. Doctor aggregates checks into a health score. Config and logging use XDG paths. Templates are embedded f-strings. All output flows through Rich.

**Key design decisions:**
- Templates: embedded Python strings (no importlib.resources)
- Nvim: headless `Lazy sync` during setup (user's choice)
- Modules must not import from each other — all shared code lives in `utils/`
- All subprocess calls go through `utils/shell.py` `run_command()`
- Full type hints, docstrings, pathlib everywhere, no bare `except:`

---

## File Tree (23 files)

```
devpilot/
├── pyproject.toml
├── README.md
├── .github/workflows/ci.yml
└── src/devpilot/
    ├── __init__.py
    ├── cli/
    │   ├── __init__.py
    │   └── main.py
    ├── modules/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── git/
    │   │   ├── __init__.py
    │   │   └── module.py
    │   ├── python/
    │   │   ├── __init__.py
    │   │   └── module.py
    │   ├── node/
    │   │   ├── __init__.py
    │   │   └── module.py
    │   ├── cpp/
    │   │   ├── __init__.py
    │   │   └── module.py
    │   ├── vscode/
    │   │   ├── __init__.py
    │   │   └── module.py
    │   └── nvim/
    │       ├── __init__.py
    │       └── module.py
    ├── doctor/
    │   ├── __init__.py
    │   └── runner.py
    ├── config/
    │   ├── __init__.py
    │   └── manager.py
    ├── logging/
    │   ├── __init__.py
    │   └── logger.py
    └── utils/
        ├── __init__.py
        └── shell.py
tests/
├── __init__.py
├── conftest.py
├── test_config_manager.py
├── test_shell.py
├── test_doctor_runner.py
├── test_module_git.py
├── test_module_python.py
├── test_module_node.py
├── test_module_cpp.py
├── test_module_vscode.py
├── test_module_nvim.py
```

---

## File-by-File Specification

### 1. `pyproject.toml`

Standard PEP 621. Key details:
- `name = "devpilot"`, version `0.1.0`
- `requires-python = ">=3.12"`
- Dependencies: `typer[all]>=0.15`, `pyyaml>=6.0`, `rich>=13.0`
- Dev dependencies: `pytest>=8.0`, `pytest-mock>=3.14`, `ruff>=0.8`, `black>=24.0`, `mypy>=1.0`
- `[project.scripts]`: `devpilot = "devpilot.cli.main:app"`
- `[tool.ruff]` config: line-length 100, target-version py312, select E/F/I/N/W/UP
- `[tool.black]` config: line-length 100, target-version py312
- `[tool.mypy]` config: strict = true, python_version 3.12
- `[tool.pytest.ini_options]`: testpaths = "tests"

### 2. `README.md`

Standard markdown: overview, quickstart (`pipx install .` → `devpilot setup`), all CLI commands with brief examples, requirements (WSL2 Ubuntu 22.04+), project structure diagram.

### 3. `.github/workflows/ci.yml`

On push/PR to main. Steps: checkout, setup python 3.12, install deps, ruff check, black --check, mypy src/, pytest -v.

---

### 4. `src/devpilot/__init__.py`

```python
"""DevPilot — Developer workstation bootstrapper for WSL2 Ubuntu."""
```

### 5. `src/devpilot/cli/__init__.py`

Empty.

### 6. `src/devpilot/cli/main.py`

**This is the Typer entrypoint.**

```python
app = typer.Typer(help="DevPilot — WSL2 developer workstation bootstrapper")
```

Commands:

- `devpilot info` — Gathers system info:
  - `lsb_release -a` for Ubuntu version
  - `uname -r` for kernel
  - `/proc/version` grep for "microsoft" → WSL2 or WSL1
  - `nproc` for CPU cores, `/proc/meminfo` MemTotal for RAM
  - `df -h /` for disk
  - Renders as a Rich Table with two columns (Property, Value)

- `devpilot doctor` — Instantiates all 6 modules, calls `doctor()` on each, aggregates `List[CheckResult]`, computes health score: `(passed_checks / total_checks) * 100` rounded to int. Displays each check with ✅ (passed), ⚠️ (warning), ❌ (failed). Shows final `[bold]Health Score: X/100[/bold]` panel.

- `devpilot setup [module_name]` — Without arg: install all 6 modules in order (git→python→node→cpp→vscode→nvim). With arg: install just that one. Uses `rich.progress.Progress` with a single `Progress` bar (`BarColumn`, `TextColumn` for module name). Each module's `install()` is called; on success, config updated via `ConfigManager.mark_installed()`. On failure, error logged and displayed but continues to next module.

- `devpilot init [template] [project_name]` — Available templates: `cpp`, `python`, `cli`. Creates directory `project_name/` in CWD with scaffold. `cpp` template: `CMakeLists.txt`, `src/main.cpp`, `.gitignore`. `python` template: `pyproject.toml`, `src/project_name/__init__.py`, `src/project_name/main.py`, `tests/__init__.py`, `tests/test_main.py`, `.gitignore`. `cli` template: same as python but with Typer CLI boilerplate in main.py. All template content embedded as f-strings using `project_name` variable.

Organize with 4 top-level functions decorated with `@app.command()`. Extract system-info gathering into a helper `get_system_info() -> dict`.

---

### 7. `src/devpilot/modules/__init__.py`

Empty.

### 8. `src/devpilot/modules/base.py`

```python
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class CheckResult:
    name: str          # e.g. "git installed"
    passed: bool
    message: str       # e.g. "git version 2.43.0 found"
    fix: str | None    # e.g. "Run: sudo apt install git"

class BaseModule(ABC):
    name: str  # class-level attribute, set in subclass

    @abstractmethod
    def install(self) -> bool: ...

    @abstractmethod
    def verify(self) -> list[CheckResult]: ...

    @abstractmethod
    def doctor(self) -> list[CheckResult]: ...
```

Doctor calls verify() and can add module-specific additional checks. The `name` attribute is used by CLI for display and logging.

---

### 9–14. Module Implementations

Each follows the same pattern with `name`, `install()`, `verify()`, `doctor()`.

- **git**: apt-install git, prompt for user.name/email if missing
- **python**: apt-install python3/pip/venv, test venv create+import
- **node**: NodeSource LTS script, typescript globally
- **cpp**: build-essential+gcc/clang/cmake/gdb, compile hello world
- **vscode**: detect code in PATH, check WSL extension
- **nvim**: neovim+ripgrep+fd-find, deploy lazy.nvim config, headless Lazy sync

---

### 15. `src/devpilot/doctor/runner.py`

```python
def run_all_doctors(modules: list) -> tuple[list[CheckResult], int]:
    """Run doctor() on all modules. Returns (all_results, health_score)."""
```

Health score: `round((passed / total) * 100)` if total > 0 else 100.

### 16. `src/devpilot/config/manager.py`

ConfigManager with load/save YAML to `~/.config/devpilot/config.yaml`. Schema: `installed_modules: []`, `preferences: {default_editor, default_shell, auto_update}`.

### 17. `src/devpilot/logging/logger.py`

TimedRotatingFileHandler, daily rotation, 7-day retention. Logs to `~/.local/share/devpilot/logs/devpilot.log`.

### 18. `src/devpilot/utils/shell.py`

`run_command()`, `which()`, `apt_install()` — all subprocess goes through here.

### 19–27. Tests

Test files for config, shell, doctor, and all 6 modules. Use pytest-mock for subprocess mocking.

---

## Implementation Order

1. `pyproject.toml`, `README.md`, `.github/workflows/ci.yml`
2. `src/devpilot/__init__.py`, `utils/shell.py`, `logging/logger.py`, `config/manager.py`
3. `modules/base.py`, `modules/git/`, `modules/python/`
4. `modules/node/`, `modules/cpp/`, `modules/vscode/`
5. `modules/nvim/` (most complex)
6. `doctor/runner.py`
7. `cli/main.py` (wires everything together)
8. All test files
9. Final verification
