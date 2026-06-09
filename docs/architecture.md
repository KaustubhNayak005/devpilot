# DevPilot — Architecture

## Overview

DevPilot is a Python CLI application for managing WSL2 Ubuntu developer workstations.
It is organized into independent subsystems that communicate through well-defined interfaces.

## Layer diagram

```
CLI Layer (Typer)
│
├── Module System    install / verify / doctor for each dev tool
├── AI Subsystem     diagnose failures, answer questions, suggest fixes
├── Inspector Subsystem  scan repos, detect stacks, identify missing tools
└── Snapshot Subsystem   capture, store, diff, restore workstation state
```

## CLI layer (`devpilot/cli/`)

Entry point for all commands. Uses Typer for argument parsing and command routing.
All user-facing output goes through Rich — never raw print().

## Module system (`devpilot/modules/`)

Each tool (Git, Python, Node.js, etc.) is a class that inherits BaseModule.
BaseModule defines three methods every module must implement:
- `install()` — installs the tool
- `verify()` — returns True if the tool is correctly installed
- `doctor()` — returns a structured health check result

New tools are added by creating a new module class — no CLI changes required.

## AI subsystem (`devpilot/ai/`)

Wraps LLM providers behind a common interface. Accepts structured failure data
and system context, returns structured diagnoses with suggested fixes.
Providers: OpenAI, Anthropic, Gemini, Ollama (see `devpilot/ai/providers/`).
API keys and model selection are read from environment variables (set via .env).

## Inspector subsystem (`devpilot/inspector/`)

Scans a project directory (max depth 3) for stack indicator files.
Maps detected stacks to required tools. Checks which tools are installed.
Offers to install missing tools using apt or documented manual steps.

## Snapshot subsystem (`devpilot/snapshot/`)

Captures workstation state: apt packages, git config, environment variables,
SHA256 hashes of dotfiles, and DevPilot config. Stores as JSON in
`~/.config/devpilot/snapshots/`. Restore re-installs missing packages and
prompts the user before touching any config file.

## Configuration

Runtime configuration lives in `~/.config/devpilot/config.yaml`.
Secrets and provider selection live in `.env` (never committed to version control).
`.env.example` documents all available variables.

## Data flow: `devpilot doctor --ai`

```
User runs command
│
▼
CLI layer calls doctor runner
│
▼
Doctor runner executes all module.verify() checks
│
▼
Failures collected as list[dict]
│
▼
context.gather_context() collects system info
│
▼
ai/client.py sends prompt to selected provider
│
▼
Response parsed into DiagnosisResult dataclasses
│
▼
Rich panel displays root cause + explanation + fix
│
▼
User confirms → subprocess runs fix → re-verify
```
