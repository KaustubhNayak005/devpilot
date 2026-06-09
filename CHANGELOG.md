# Changelog

All notable changes to DevPilot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

## [0.2.0] — In progress

### Added
- AI-powered doctor: detect broken environment, explain root cause, suggest and
  optionally auto-run fix (`devpilot doctor --ai`)
- Free-form AI questions about your environment (`devpilot ask "<question>"`)
- Project-aware stack detection (`devpilot inspect <path>`) — scans any repo
  and identifies missing tools for Flutter, C++, Rust, Go, Node.js, Python, Docker
- Environment snapshots (`devpilot snapshot save/list/restore/diff`) — capture
  and restore full workstation state
- Multi-provider AI support: OpenAI, Anthropic, Gemini, Ollama
- Developer profiles (`devpilot profile install <name>`)
- .env-based configuration — no more hardcoded API keys
- GitHub Actions CI/CD pipeline with lint, type-check, test, and build jobs
- Code coverage reporting via Codecov

### Changed
- API key handling moved from environment export to .env file
- Install order moved from hardcoded list to dependency graph

### Fixed
- (fill in as bugs are fixed)

## [0.1.0] — Initial release

### Added
- `devpilot setup` — install Git, Python, Node.js, C/C++, VS Code, Neovim
- `devpilot doctor` — health checks for all installed modules
- `devpilot info` — system information display
- `devpilot init` — project scaffolding
- BaseModule system with install/verify/doctor contract
- Rich CLI with progress bars and panels
- YAML config for tracking installed modules
