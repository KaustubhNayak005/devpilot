# Changelog

All notable changes to DevPilot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

## [0.2.0] — 2026-06-09

### Added
- AI-powered doctor: detect broken environment, explain root cause, suggest and
  optionally auto-run fix (`devpilot doctor --ai`)
- Free-form AI questions about your environment (`devpilot ask "<question>"`)
- Project-aware stack detection (`devpilot inspect <path>`) — scans any repo
  and identifies missing tools for Flutter, C++, Rust, Go, Node.js, Python, Docker
- Environment snapshots (`devpilot snapshot save/list/restore/diff`) — capture
  and restore full workstation state
- Multi-provider AI support: OpenAI, Anthropic, Gemini, Ollama
- Developer profiles (`devpilot profile install <name>`) — 6 curated profiles
- `.env`-based configuration via `python-dotenv` — API keys in `.env`, never committed
- GitHub Actions CI/CD pipeline (4 jobs: lint, type-check, test, build-verify)
- `--version` flag on CLI entrypoint
- `--fix` flag on doctor for offline self-healing (`devpilot doctor --fix`)
- Code coverage reporting via Codecov (109 tests, fail_under=70)
- Issue templates (bug report, feature request)

### Changed
- API key handling moved from `os.environ["KEY"]` to `os.environ.get("KEY")` with `.env` loading
- Install order replaced hardcoded `INSTALL_ORDER` list with dependency graph + topological sort
- BaseModule now has `dependencies: list[str] = []` class attribute
- Provider architecture: single OpenAI client replaced with AIProvider ABC + factory
- Architecture docs rewritten for v0.2.0 completeness
- Documentation consolidated into `docs/` folder

### Fixed
- Syntax error in `doctor/fixes.py` (garbage lines after FIXES dict closing)
- Import of nonexistent `_get_api_key` from `test_ai.py`
- Duplicate `test_ask_returns_response` function in `test_ai.py`
- Missing `Callable` import in `doctor/fixes.py`
- Providers `__init__.py` eager imports crashing when optional SDKs not installed
- Factory graceful degradation when optional providers can't be imported
- Test patches targeting wrong modules (runner, factory, providers)

## [0.1.0] — Initial release

### Added
- `devpilot setup` — install Git, Python, Node.js, C/C++, VS Code, Neovim
- `devpilot doctor` — health checks for all installed modules
- `devpilot info` — system information display
- `devpilot init` — project scaffolding (cpp, python, cli templates)
- BaseModule system with install/verify/doctor contract
- Rich CLI with progress bars and panels
- YAML config for tracking installed modules
- Shell utility safety model (no shell=True, list args, timeouts)
