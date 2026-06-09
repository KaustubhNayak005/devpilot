# DevPilot Architecture

## Overview

DevPilot is a CLI tool that automates the setup of a complete WSL2 Ubuntu developer workstation. Think of it as Homebrew + Oh My Zsh combined, purpose-built for the WSL2 environment. One command boots a bare Ubuntu install into a fully equipped dev machine.

**Core principle**: Every tool is managed by a module. Modules are self-contained, independently testable, and follow a strict ABC contract. The CLI orchestrates them — modules never know about each other.

## High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Layer (Typer)                    │
│  devpilot info  │  devpilot doctor  │  devpilot setup   │
│                 │                    │  devpilot init    │
└──────┬──────────┴────────┬───────────┴────────┬─────────┘
       │                   │                    │
       ▼                   ▼                    ▼
┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐
│  System Info │  │  Doctor Runner  │  │  Module System   │
│  (inline fn) │  │  (aggregates    │  │  (BaseModule ABC)│
│              │  │   all modules)  │  │                  │
└──────────────┘  └────────┬────────┘  └────────┬─────────┘
                           │                    │
                           ▼                    ▼
                  ┌──────────────────────────────────────┐
                  │          6 Modules                    │
                  │  git │ python │ node │ cpp │ vscode  │
                  │                    │ nvim            │
                  └──────────┬───────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
      ┌──────────┐   ┌──────────┐   ┌──────────────┐
      │  Config  │   │  Logging │   │  Shell Utils │
      │  Manager │   │  Logger  │   │  (shared)    │
      │  (YAML)  │   │ (rotate) │   │              │
      └──────────┘   └──────────┘   └──────────────┘
```

## Directory Structure

```
devpilot/
├── pyproject.toml              # Build config, deps, tool settings, entrypoint
├── README.md                   # User-facing documentation
├── ARCHITECTURE.md             # This file — system architecture
├── DEEP_DIVE.md                # Exhaustive walkthrough of every component
├── .github/workflows/ci.yml    # CI: ruff, black, mypy, pytest on push/PR
│
├── src/devpilot/
│   ├── __init__.py             # Package marker with docstring
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py             # Typer entrypoint — all 4 commands + scaffolding
│   │
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── base.py             # BaseModule ABC + CheckResult dataclass
│   │   ├── git/module.py       # GitModule: git + global config
│   │   ├── python/module.py    # PythonModule: python3, pip, venv
│   │   ├── node/module.py      # NodeModule: Node.js LTS + TypeScript
│   │   ├── cpp/module.py       # CppModule: GCC, Clang, CMake, GDB, Make
│   │   ├── vscode/module.py    # VSCodeModule: code CLI + WSL extension
│   │   └── nvim/module.py      # NvimModule: Neovim + full lazy.nvim config
│   │
│   ├── doctor/
│   │   ├── __init__.py
│   │   └── runner.py           # Aggregates doctor() across modules → health score
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── manager.py          # ~/.config/devpilot/config.yaml read/write
│   │
│   ├── logging/
│   │   ├── __init__.py
│   │   └── logger.py           # TimedRotatingFileHandler, 7-day retention
│   │
│   └── utils/
│       ├── __init__.py
│       └── shell.py            # run_command(), which(), apt_install()
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # Shared fixtures (temp config, mocks)
    ├── test_config_manager.py  # ConfigManager unit tests
    ├── test_doctor_runner.py   # Health score logic tests
    ├── test_shell.py           # run_command, which, apt_install tests
    ├── test_module_git.py      # GitModule.verify() tests
    ├── test_module_python.py   # PythonModule.verify() tests
    ├── test_module_node.py     # NodeModule.verify() tests
    ├── test_module_cpp.py      # CppModule.verify() tests
    ├── test_module_vscode.py   # VSCodeModule.verify() tests
    └── test_module_nvim.py     # NvimModule.verify() tests
```

## Module System Design

### BaseModule ABC

Every module inherits from `BaseModule` and must implement three methods:

```
BaseModule (ABC)
├── name: str                              ← class attribute
├── install() -> bool                      ← install tools + configure
├── verify() -> list[CheckResult]          ← post-install verification
└── doctor() -> list[CheckResult]          ← comprehensive health check
```

### CheckResult Dataclass

A frozen dataclass representing a single check outcome:

| Field   | Type          | Purpose                              |
| ------- | ------------- | ------------------------------------ |
| name    | str           | Human-readable check name            |
| passed  | bool          | Whether the check succeeded          |
| message | str           | Descriptive result message           |
| fix     | str \| None   | Suggested fix command, if failed     |

### Module Contract

1. **No cross-module imports.** Modules reference only `base.py` and `utils/shell.py`. They never import from each other. This guarantees modules are independently testable and replaceable.

2. **Self-contained install.** Each `install()` method handles its own dependency resolution. For apt packages, use `apt_install()` from shell utils. For custom setup (like NodeSource), handle it internally.

3. **Idempotency.** `install()` checks `which()` before installing. Running `setup` twice won't break anything.

4. **Verify is headless.** `verify()` only uses CLI commands — no prompts, no interactive input.

5. **Doctor = Verify for simple modules.** Most modules delegate `doctor()` to `verify()`. A module can override `doctor()` for deeper checks (e.g., network tests, filesystem permissions).

## CLI Layer

### Entrypoint

The `pyproject.toml` defines the console script:

```toml
[project.scripts]
devpilot = "devpilot.cli.main:app"
```

After `pipx install`, typing `devpilot` invokes the Typer app.

### Command Tree

| Command               | Function              | Purpose                                  |
| --------------------- | --------------------- | ---------------------------------------- |
| `devpilot info`       | `info()`              | Display system info in Rich table        |
| `devpilot doctor`     | `doctor()`            | Run all health checks, compute score     |
| `devpilot setup`      | `setup()`             | Install all 6 modules in order           |
| `devpilot setup <m>`  | `setup(module_name)`  | Install a single module                  |
| `devpilot init <t> <n>` | `init(template, project_name)` | Scaffold a new project      |

### System Info Gathering

`_get_system_info()` reads from:
- `lsb_release` → Ubuntu version
- `uname -r` → kernel version
- `/proc/version` → WSL detection (looks for "icrosoft" / "WSL" markers)
- `nproc` → CPU core count
- `/proc/meminfo` → RAM (parses MemTotal, converts to GB)
- `df -h /` → disk usage

All readings are wrapped in try/except — unknown fields show "Unknown" rather than crashing.

### Module Installation Order

`devpilot setup` installs modules in this fixed order:

```
git → python → node → cpp → vscode → nvim
```

Rationale: git is dependency-free. python and node are prerequisites for some tools. cpp is heavy but self-contained. vscode is a detection-only module. nvim depends on node (for Mason/cmp) and goes last.

Each successful install is persisted to `config.yaml` via `ConfigManager.mark_installed()`.

### Rich Output Policy

All terminal output uses Rich. No bare `print()` exists in the codebase:
- `Rich Table` for `info` system data
- `Rich Panel` for doctor header and health score
- `Rich Progress` bar for `setup` multi-install
- `Rich Console` for colorized error/warning messages

## Config Subsystem

**Location**: `~/.config/devpilot/config.yaml`

**Schema**:
```yaml
installed_modules:
  - git
  - python
preferences:
  default_editor: code
  default_shell: bash
  auto_update: "true"
```

**Lifecycle**: 
1. `ConfigManager.load()` checks if the file exists. If not, returns defaults (`{"installed_modules": [], "preferences": {}}`).
2. On corrupted YAML, returns defaults silently (no crash).
3. `mark_installed(name)` loads → appends if not present → saves.
4. Preferences are key-value strings with defaults via `get_preference(key, default)`.

## Logging Subsystem

**Location**: `~/.local/share/devpilot/logs/devpilot.log`

**Format**: `[2024-01-15 14:30:00][INFO][git] git installed successfully.`

**Rotation**: Daily at midnight, 7-day retention (`TimedRotatingFileHandler`).

**Usage**: Modules get a logger via `logging.getLogger("devpilot")` and log at appropriate levels (info for success, warning for soft failures, error for hard failures, exception for unhandled errors).

## Shell Utilities (Safety Model)

All subprocess calls go through `run_command()` in `utils/shell.py`. Key safety properties:

1. **No `shell=True`.** Commands are passed as lists of strings, eliminating shell injection.
2. **Text mode** — stdout/stderr are strings, not bytes.
3. **Timeout protection** — default 300s, prevents hanging.
4. **Explicit check** — raises `CalledProcessError` only when `check=True`.
5. **Working directory** — `cwd` parameter accepts `Path` objects.

`which()` wraps `shutil.which()` returning `Path | None`.

`apt_install()` is a convenience wrapper that runs `sudo apt-get install -y` with a 600s timeout and handles `TimeoutExpired`/`OSError`/`FileNotFoundError` gracefully.

## Package & Release Model

- **Build system**: Hatchling (`hatchling.build`)
- **Install**: `pipx install .` (isolated venv, global CLI access)
- **Python**: 3.12+ (uses `str | None` syntax, `pathlib.Path`, no deprecated APIs)
- **Deps**: Typer[all] for CLI, PyYAML for config, Rich for terminal UI
- **Dev deps**: pytest, ruff, black, mypy

## Design Decisions

| Decision | Rationale |
| -------- | --------- |
| **Rich over print()** | Consistent terminal UI with tables, panels, progress bars, colors. Zero-effort polish. |
| **Path everywhere** | `pathlib.Path` for all filesystem operations. No string paths. OS-safe, readable. |
| **list subprocess args** | `run_command(["apt", "install", pkg])` not `run_command("apt install " + pkg)`. Prevents injection. |
| **CheckResult dataclass** | Structured result type shared across all modules. Enables aggregation and tabular display. |
| **Separate verify/doctor** | verify = quick post-install check. doctor = comprehensive health audit. Modules can inherit verify for simplicity. |
| **No cross-module imports** | Each module is an island. Easy to add/remove modules. Tests don't cascade. |
| **TimedRotatingFileHandler** | Standard library solution. No external log dependency. Daily rotation matches dev workflow. |
| **YAML config over JSON** | More readable for hand-editing. PyYAML is the only extra dep. |
