# DevPilot Architecture

## Overview

DevPilot is a Python CLI application for managing WSL2 Ubuntu developer workstations. Version 0.2.0 spans nine subsystems that communicate through well-defined interfaces: a module system for tool management, an AI subsystem for intelligent diagnostics, an inspector for project-aware stack detection, a snapshot system for workstation state capture/restore, developer profiles for curated tool bundles, and a self-healing doctor with offline and AI-powered fix modes.

## High-Level Component Diagram

```
CLI Layer (Typer)
      │
      ├── Module System           install / verify / doctor for each dev tool
      ├── AI Subsystem            diagnose failures, answer questions, suggest fixes
      ├── Inspector Subsystem     scan repos, detect stacks, identify missing tools
      ├── Snapshot Subsystem      capture, store, diff, restore workstation state
      └── Profiles Subsystem      curated bundles of tools for specific workflows
```

## Directory Structure

```
devpilot/
├── pyproject.toml
├── README.md
├── .env.example                     # Template for AI provider config
├── .gitignore
├── .github/
│   ├── workflows/ci.yml             # CI: lint, type-check, test, build
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
│
├── src/devpilot/
│   ├── __init__.py                  # load_dotenv() — env vars available everywhere
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py                  # Typer app: info, doctor, ask, inspect,
│   │                                #   setup, profile, snapshot, init
│   │
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── base.py                  # BaseModule ABC + CheckResult dataclass
│   │   ├── resolver.py              # Topological sort (Kahn's algorithm)
│   │   ├── git/module.py            # GitModule
│   │   ├── python/module.py         # PythonModule
│   │   ├── node/module.py           # NodeModule
│   │   ├── cpp/module.py            # CppModule
│   │   ├── vscode/module.py         # VSCodeModule
│   │   └── nvim/module.py           # NvimModule
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── base.py                  # AIProvider ABC, DiagnosisResult, prompt templates
│   │   ├── client.py                # Public API: diagnose(), ask()
│   │   ├── context.py               # gather_context() — system info for AI
│   │   ├── factory.py               # get_provider() — reads env var, returns provider
│   │   └── providers/
│   │       ├── __init__.py           # Lazy-loaded to handle optional deps
│   │       ├── openai.py             # OpenAIProvider
│   │       ├── anthropic.py          # AnthropicProvider
│   │       ├── gemini.py             # GeminiProvider
│   │       └── ollama.py             # OllamaProvider
│   │
│   ├── doctor/
│   │   ├── __init__.py
│   │   ├── runner.py                 # run_all_doctors(), _run_fixes(), _run_ai_diagnosis()
│   │   └── fixes.py                  # FIXES dict: module name → fix function
│   │
│   ├── inspector/
│   │   ├── __init__.py
│   │   ├── detector.py               # detect_stack() — file-based stack detection
│   │   ├── checker.py                # check_tools() — PATH availability check
│   │   └── installer.py              # install_missing() — apt-based tool install
│   │
│   ├── snapshot/
│   │   ├── __init__.py
│   │   ├── capture.py                # Snapshot dataclass, capture_snapshot()
│   │   ├── storage.py                # save/load/list snapshots as JSON
│   │   ├── diff.py                   # diff_snapshots() — compare saved vs current
│   │   └── restore.py                # restore_snapshot() — interactive restore
│   │
│   ├── profiles/
│   │   ├── __init__.py
│   │   ├── definitions.py            # Profile dataclass + PROFILES registry (6 profiles)
│   │   └── installer.py              # install_profile() — apt/pip/npm runner
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── manager.py                # ~/.config/devpilot/config.yaml R/W
│   │
│   ├── logging/
│   │   ├── __init__.py
│   │   └── logger.py                 # TimedRotatingFileHandler, 7-day retention
│   │
│   └── utils/
│       ├── __init__.py
│       └── shell.py                  # run_command(), which(), apt_install()
│
├── docs/
│   ├── ARCHITECTURE.md               # This file
│   ├── CHANGELOG.md                  # Release history
│   ├── DEEP_DIVE.md                  # Exhaustive component walkthrough
│   └── IMPLEMENTATION_PLAN.md        # Original blueprint (historical)
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_ai.py                    # Context and client tests
    ├── test_ai_factory.py            # Provider factory tests
    ├── test_config_manager.py
    ├── test_doctor_fixes.py          # Fix functions and runner integration
    ├── test_doctor_runner.py
    ├── test_inspector.py             # Detector, checker, installer tests
    ├── test_module_git.py
    ├── test_module_python.py
    ├── test_module_node.py
    ├── test_module_cpp.py
    ├── test_module_vscode.py
    ├── test_module_nvim.py
    ├── test_profiles.py              # Profile definitions and installer tests
    ├── test_resolver.py              # Topological sort tests
    ├── test_shell.py
    └── test_snapshot.py              # Capture, storage, diff tests
```

## CLI Layer (`devpilot/cli/`)

Entry point for all commands. Uses Typer for argument parsing and command routing. All user-facing output goes through Rich — never raw `print()`. Configuration loads from `.env` via `python-dotenv` in `devpilot/__init__.py`.

### Command Tree

| Command | Flags | Purpose |
| --- | --- | --- |
| `devpilot info` | | Display system info in Rich table |
| `devpilot --version` | | Show version and exit |
| `devpilot doctor` | `--ai`, `--fix` | Run health checks, compute score |
| `devpilot ask <question>` | | AI expert Q&A about environment |
| `devpilot inspect [path]` | | Scan repo for project stacks |
| `devpilot setup [module]` | | Install modules (topological order) |
| `devpilot profile list` | | List available profiles |
| `devpilot profile show <name>` | | Show profile contents |
| `devpilot profile install <name>` | `--dry-run` | Install a profile |
| `devpilot snapshot save <name>` | | Capture environment state |
| `devpilot snapshot list` | | List saved snapshots |
| `devpilot snapshot restore <name>` | | Restore from snapshot |
| `devpilot snapshot diff <name>` | | Compare saved vs current |
| `devpilot init <t> <name>` | | Scaffold new project |

## Module System (`devpilot/modules/`)

Each tool (Git, Python, Node.js, etc.) is a class that inherits `BaseModule`. Six modules ship with DevPilot:

| Module | Class | Dependencies |
| --- | --- | --- |
| git | `GitModule` | none |
| python | `PythonModule` | none |
| node | `NodeModule` | none |
| cpp | `CppModule` | none |
| vscode | `VSCodeModule` | none |
| nvim | `NvimModule` | none |

### BaseModule Contract

```
BaseModule (ABC)
├── name: str                              ← class attribute
├── dependencies: list[str] = []           ← topological sort input
├── install() -> bool                      ← install tools + configure
├── verify() -> list[CheckResult]          ← post-install verification
└── doctor() -> list[CheckResult]          ← comprehensive health check
```

### Module Install Order (via topological sort)

`devpilot/modules/resolver.py` implements Kahn's algorithm. When all dependencies are `[]`, the resolver returns modules in any order. When dependencies are declared, the resolver guarantees dependents come after their dependencies. Circular dependencies raise `ValueError`.

## AI Subsystem (`devpilot/ai/`)

Wraps LLM providers behind a common `AIProvider` ABC. The factory (`factory.py`) reads `DEVPILOT_AI_PROVIDER` from the environment (loaded via `.env`) and returns the matching provider. If unset, it auto-detects the first available provider by checking `is_available()` on each. Lazy imports with try/except ensure missing optional SDKs don't block startup.

### Providers

| Provider | Required Env Vars | SDK |
| --- | --- | --- |
| OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL` | `openai` |
| Anthropic | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | `anthropic` |
| Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL` | `google-generativeai` |
| Ollama | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | `requests` |

### Data Flow: `devpilot doctor --ai`

```
User runs command
      │
      ▼
CLI layer calls doctor runner
      │
      ▼
Doctor runner executes all module.doctor() checks
      │
      ▼
Failures collected as list[dict]
      │
      ▼
context.gather_context() collects system info
      │
      ▼
ai/client.py delegates to provider via factory
      │
      ▼
Provider sends prompt, parses response into DiagnosisResult
      │
      ▼
Rich panel displays root cause + explanation + fix
      │
      ▼
User confirms → subprocess runs fix → re-verify
```

## Doctor Subsystem (`devpilot/doctor/`)

### `--fix` mode (offline)
Uses hardcoded known-good fixes from `fixes.py`. Each module has a fix function that re-installs the tool via apt. Runs without any LLM — works fully offline.

### `--ai` mode (online)
Sends failure data + system context to the configured AI provider. Returns structured `DiagnosisResult` objects with root cause analysis and safe shell commands.

### `--fix --ai` combined
Offline fixes run first. Any module that still fails after fix is passed to the AI for deeper diagnosis.

## Inspector Subsystem (`devpilot/inspector/`)

Scans a project directory (max depth 3) for stack indicator files:

| Stack | Detection Files |
| --- | --- |
| Flutter | `pubspec.yaml` |
| C++ | `CMakeLists.txt` |
| Rust | `Cargo.toml` |
| Go | `go.mod` |
| Node.js | `package.json` |
| Python | `pyproject.toml`, `requirements.txt` |
| Docker | `Dockerfile` |

Maps detected stacks to required tools. Checks which tools are installed (via `which()`). Offers to install missing tools via apt or documents manual install steps.

## Snapshot Subsystem (`devpilot/snapshot/`)

Captures workstation state: apt packages, git config, environment variables, SHA-256 hashes of dotfiles, and DevPilot config. Stores as JSON in `~/.config/devpilot/snapshots/`. Restore re-installs missing packages interactively. Diff shows added/removed packages, changed env vars, and modified config files.

## Profiles Subsystem (`devpilot/profiles/`)

Six curated profiles ship with DevPilot:

| Profile | Target Workflow |
| --- | --- |
| `cpp` | C++ development — compiler, debugger, build tools, LSP |
| `python` | Python development — interpreter, linters, formatters |
| `flutter` | Flutter/Dart mobile and web |
| `ai-engineer` | AI/ML — Python stack, popular frameworks |
| `competitive-programming` | Fast compilers, debuggers, contest tools |
| `fullstack` | Node.js + Python + Docker |

Each profile defines apt, pip, and npm package lists plus post-install notes. The installer runs packages in order: apt → pip → npm, then displays notes. `--dry-run` previews without executing.

## Configuration

- **Runtime config**: `~/.config/devpilot/config.yaml` (YAML, tracks installed modules and preferences)
- **Secrets/provider**: `.env` in project root (never committed, `.env.example` documents all variables)
- **Snapshots**: `~/.config/devpilot/snapshots/` (JSON files)
- **Logs**: `~/.local/share/devpilot/logs/` (daily rotating, 7-day retention)

## Design Decisions

| Decision | Rationale |
| --- | --- |
| Lazy provider imports | Missing optional SDKs (anthropic, gemini) don't block startup |
| Topological sort over hardcoded order | Modules declare dependencies; resolver handles ordering |
| `--fix` separate from `--ai` | Offline fixes are instant and work without API keys |
| Profiles as data (not code) | Adding a profile is adding a dataclass instance |
| Snapshots as JSON | Human-inspectable, easy to diff, no binary format |
| `.env` + `python-dotenv` | Standard pattern, secrets never committed, env vars available everywhere |
