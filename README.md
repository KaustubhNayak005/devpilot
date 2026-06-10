# DevPilot

[![CI](https://github.com/user/devpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/user/devpilot/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/badge/lint-ruff-261230)](https://docs.astral.sh/ruff/)
[![Mypy](https://img.shields.io/badge/typecheck-mypy-blue)](https://mypy-lang.org/)
[![Coverage](https://img.shields.io/badge/coverage-109%20tests-brightgreen)]()

**AI-powered developer workstation bootstrapper for WSL2 Ubuntu.**

One command to set up your entire WSL2 development environment — like Homebrew + Oh My Zsh combined, purpose-built for WSL2. Now with multi-provider AI diagnostics, project stack detection, environment snapshots, and developer profiles.

## Requirements

- Windows 10/11 with WSL2 enabled
- Ubuntu 22.04 or 24.04 running inside WSL2
- Python 3.12 or later
- `pipx` installed (`sudo apt install pipx && pipx ensurepath`)

## Quickstart

```bash
# Copy environment config
cp .env.example .env
# Edit .env with your AI provider and API keys

# Install DevPilot
pipx install .

# Bootstrap everything
devpilot setup

# Check your environment health
devpilot doctor

# See what you're running
devpilot info
```

## Configuration (.env)

Copy `.env.example` to `.env` and configure your AI provider:

```env
DEVPILOT_AI_PROVIDER=openai      # openai | anthropic | gemini | ollama
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

All AI features (`devpilot doctor --ai`, `devpilot ask`) read from this file. The `.env` file is git-ignored so you never commit secrets.

## Commands

### `devpilot info`

Display system information in a Rich table.

```bash
devpilot info
devpilot --version
```

**Output includes:** Ubuntu version, WSL version, kernel, CPU cores, RAM, disk usage.

### `devpilot doctor`

Run health checks across all installed modules. Supports offline auto-fix and AI-powered diagnosis.

```bash
devpilot doctor                 # health check only
devpilot doctor --fix           # auto-fix failures with known fixes (offline)
devpilot doctor --ai            # AI-powered root cause analysis + suggested fixes
devpilot doctor --fix --ai      # auto-fix first, then AI handles remaining failures
```

**Scoring:**
- `90–100` — green, your environment is healthy
- `60–89` — yellow, some issues need attention
- `0–59` — red, significant problems

### `devpilot ask`

Ask an AI expert a free-form question about your WSL2 Ubuntu dev environment.

```bash
devpilot ask "why is my cmake build failing with linker errors?"
devpilot ask "how do I set up CUDA for PyTorch?"
```

### `devpilot inspect`

Scan a project directory and detect what tools are needed.

```bash
devpilot inspect                      # scan current directory
devpilot inspect ~/projects/my-app   # scan a specific path
```

**Detected stacks:** Flutter, C++, Rust, Go, Node.js, Python, Docker. Reports missing tools and offers to install them.

### `devpilot setup`

Install development tools with a Rich progress bar. Uses topological sort based on module dependency declarations.

```bash
devpilot setup           # install all 6 modules in dependency-safe order
devpilot setup python    # install just python
devpilot setup nvim      # install just neovim
devpilot setup node      # install just Node.js
```

**Modules installed:**

| Module    | Tools installed                                                    |
| --------- | ------------------------------------------------------------------ |
| git       | git, global `user.name` / `user.email` configuration              |
| python    | python3, pip, venv                                                |
| node      | Node.js LTS (via NodeSource), npm, TypeScript globally            |
| cpp       | GCC, G++, Clang, CMake, GDB, Make                                 |
| vscode    | Detects VS Code CLI, validates Remote-WSL extension               |
| nvim      | Neovim, ripgrep, fd-find; lazy.nvim config with Telescope,        |
|           | Treesitter, Mason, LSP, nvim-cmp, Gitsigns                        |

### `devpilot profile`

Install curated sets of tools for specific development workflows.

```bash
devpilot profile list                    # list available profiles
devpilot profile show cpp                # see what a profile contains
devpilot profile install cpp             # install immediately
devpilot profile install fullstack --dry-run  # preview without installing
```

**Available profiles:** `cpp`, `python`, `flutter`, `ai-engineer`, `competitive-programming`, `fullstack`.

### `devpilot snapshot`

Capture, compare, and restore your workstation state.

```bash
devpilot snapshot save my-setup    # capture current environment
devpilot snapshot list             # list saved snapshots
devpilot snapshot diff my-setup    # compare saved vs current
devpilot snapshot restore my-setup # restore from snapshot
```

### `devpilot init`

Scaffold a new project from a template.

```bash
devpilot init python my-project     # Python project with src layout + tests
devpilot init cpp my-cpp-project    # C++ project with CMake
devpilot init cli my-cli-tool       # Python CLI project with Typer boilerplate
```

**Templates:**
- `python` — src-layout Python package with pyproject.toml, tests directory
- `cpp` — CMake project with src/main.cpp, CMakeLists.txt (C++17)
- `cli` — Python CLI app with Typer entrypoint

## Project Structure on Disk

```
~/.config/devpilot/config.yaml          # installed modules, preferences
~/.config/devpilot/snapshots/           # environment snapshots (JSON)
~/.local/share/devpilot/logs/           # rotating daily logs (7-day retention)
~/.config/nvim/init.lua                 # Neovim config deployed by nvim module
.env                                    # AI provider + API keys (never committed)
```

## Troubleshooting

### "pipx: command not found"

```bash
sudo apt update && sudo apt install pipx
pipx ensurepath
# Restart your terminal or run: source ~/.bashrc
```

### "devpilot: command not found" after pipx install

```bash
pipx ensurepath
source ~/.bashrc
```

### VS Code not detected

Install VS Code on Windows, then launch it from your WSL2 terminal once — this auto-installs the VS Code server.

### Neovim plugins not loading

Re-run `devpilot setup nvim` to redeploy the config and sync plugins. Or manually:

```bash
nvim --headless "+Lazy! sync" +qa
```

### AI features not working

Make sure your `.env` file is configured:
```bash
cp .env.example .env
# Edit .env with your API keys
```

Verify with `devpilot doctor --ai`.

### Config corrupted

Delete and regenerate:

```bash
rm ~/.config/devpilot/config.yaml
devpilot doctor
```

## Development

```bash
git clone https://github.com/user/devpilot.git
cd devpilot
pip install -e ".[dev]"

# Lint
ruff check src/ tests/

# Type check
mypy devpilot/ --ignore-missing-imports

# Test (109 tests)
pytest -v

# Test with coverage
pytest --cov=devpilot --cov-report=term-missing

# Run all checks (what CI does)
ruff check . && mypy devpilot/ --ignore-missing-imports && pytest -v
```

## Documentation

- [Architecture](./docs/ARCHITECTURE.md) — system design, component diagram, all subsystems
- [Changelog](./docs/CHANGELOG.md) — release notes and version history
- [Deep Dive](./docs/DEEP_DIVE.md) — exhaustive walkthrough of every component
- [Implementation Plan](./docs/IMPLEMENTATION_PLAN.md) — original blueprint (historical)

## License

MIT
