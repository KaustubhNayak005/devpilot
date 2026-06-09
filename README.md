# DevPilot

[![CI](https://github.com/user/devpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/user/devpilot/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/badge/lint-ruff-261230)](https://docs.astral.sh/ruff/)
[![Mypy](https://img.shields.io/badge/typecheck-mypy-blue)](https://mypy-lang.org/)

**Developer workstation bootstrapper for WSL2 Ubuntu.**

One command to set up your entire WSL2 development environment — like Homebrew + Oh My Zsh combined, purpose-built for WSL2.

## Requirements

- Windows 10/11 with WSL2 enabled
- Ubuntu 22.04 or 24.04 running inside WSL2
- Python 3.12 or later
- `pipx` installed (`sudo apt install pipx && pipx ensurepath`)

## Quickstart

```bash
# Install DevPilot
pipx install .

# Bootstrap everything
devpilot setup

# Check your environment health
devpilot doctor

# See what you're running
devpilot info
```

## Commands

### `devpilot info`

Display system information in a Rich table.

```bash
devpilot info
```

**Output includes:**
- Ubuntu version (from `lsb_release`)
- WSL version (WSL2, WSL1, or Not WSL)
- Kernel version (`uname -r`)
- CPU cores (`nproc`)
- RAM (parsed from `/proc/meminfo`)
- Disk usage (`df -h /`)

### `devpilot doctor`

Run health checks across all installed modules. Each check shows a pass/warn/fail status with fix suggestions if something is broken. A health score out of 100 is computed from the percentage of passing checks.

```bash
devpilot doctor
```

**Scoring:**
- `90-100` — green, your environment is healthy
- `60-89` — yellow, some issues need attention
- `0-59` — red, significant problems

### `devpilot setup`

Install development tools with a Rich progress bar. Running without arguments installs everything in dependency order.

```bash
devpilot setup           # install all 6 modules
devpilot setup python    # install just python
devpilot setup nvim      # install just neovim
devpilot setup node      # install just Node.js
```

**Install order:** git → python → node → cpp → vscode → nvim

**Modules installed:**

| Module    | Tools installed                                             |
| --------- | ----------------------------------------------------------- |
| git       | git, global `user.name` / `user.email` configuration        |
| python    | python3, pip, venv                                          |
| node      | Node.js LTS (via NodeSource), npm, TypeScript globally      |
| cpp       | GCC, G++, Clang, CMake, GDB, Make                           |
| vscode    | Detects VS Code CLI, validates Remote-WSL extension         |
| nvim      | Neovim, ripgrep, fd-find; lazy.nvim config with Telescope, Treesitter, Mason, LSP, nvim-cmp, Gitsigns |

### `devpilot init`

Scaffold a new project from a template.

```bash
devpilot init python my-project     # Python project with src layout + tests
devpilot init cpp my-cpp-project    # C++ project with CMake
devpilot init cli my-cli-tool       # Python CLI project with Typer boilerplate
```

**Templates:**
- `python` — src-layout Python package with pyproject.toml, tests directory, README, .gitignore
- `cpp` — CMake project with src/main.cpp, CMakeLists.txt (C++17), .gitignore
- `cli` — Python CLI app with Typer entrypoint, same structure as `python` but adds Typer dependency and console_scripts entrypoint

## Project Structure on Disk

```
~/.config/devpilot/config.yaml       # installed modules, preferences
~/.local/share/devpilot/logs/        # rotating daily logs (7-day retention)
~/.config/nvim/init.lua              # Neovim config deployed by nvim module
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

DevPilot looks for `code` in your PATH. Install VS Code on Windows, then launch it from your WSL2 terminal once — this auto-installs the VS Code server.

### Neovim plugins not loading

Re-run `devpilot setup nvim` to redeploy the config and sync plugins. Or manually:

```bash
nvim --headless "+Lazy! sync" +qa
```

### "node not found after installation"

The NodeSource setup may need curl. Install it first:

```bash
sudo apt install curl
devpilot setup node
```

### Config corrupted

Delete and regenerate:

```bash
rm ~/.config/devpilot/config.yaml
devpilot doctor  # recreated on next setup/install
```

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/user/devpilot.git
cd devpilot
pip install -e ".[dev]"

# Lint
ruff check src/ tests/

# Format
black src/ tests/

# Type check
mypy src/

# Test
pytest -v

# Run all checks (what CI does)
ruff check src/ tests/ && black --check src/ tests/ && mypy src/ && pytest -v
```

## Documentation

- [Architecture](./docs/ARCHITECTURE.md) — system design, component diagram, design decisions
- [Changelog](./docs/CHANGELOG.md) — release notes and version history
- [Deep Dive](./docs/DEEP_DIVE.md) — exhaustive walkthrough of every component
- [Implementation Plan](./docs/IMPLEMENTATION_PLAN.md) — original implementation blueprint

## License

MIT
