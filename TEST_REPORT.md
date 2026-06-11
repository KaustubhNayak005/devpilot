# DevPilot Test Report

**Generated:** 2026-06-11  
**Project:** DevPilot v0.2.0  
**Platform:** Windows (win32), Python 3.13.7  
**Branch:** master  

---

## Summary

| Metric | Result |
|--------|--------|
| Total Tests | 109 |
| Passed | 109 |
| Failed | 0 |
| Skipped | 0 |
| Duration | 6.96s |
| Lint (Ruff) | **Pass** (0 errors) |
| Type Check (Mypy) | **Pass** (0 errors, 49 source files) |
| Code Coverage | **46.02%** (45% threshold met) |

---

## Test Suite Breakdown

### AI Subsystem (18 tests)
- **test_ai.py** (10): Context gathering (OS release, PATH, env vars), diagnose parsing, invalid JSON handling, ask response
- **test_ai_factory.py** (8): Provider selection (OpenAI, Anthropic, Gemini, Ollama), fallback behavior, error handling for unknown/unconfigured providers

### Config Management (6 tests)
- **test_config_manager.py** (6): Defaults on missing file, save/load roundtrip, mark_installed dedup, preferences CRUD, corrupted YAML recovery

### Doctor Subsystem (14 tests)
- **test_doctor_fixes.py** (9): Individual fix functions (git, python, node, vscode), FIXES registry completeness/callability, fix integration with runner
- **test_doctor_runner.py** (5): Health score computation (all-passing=100, all-failing=0, mixed=50, empty=100, single mixed module)

### Inspector Subsystem (18 tests)
- **test_inspector.py** (18): Stack detection (Python, Node, C++, Rust, Go, Flutter, Docker, GitHub Actions, empty dirs, confidence levels), tool checking (all found, missing, mixed), install (success, failure, manual tools, unknown tools)

### Module Verification (18 tests)
- **test_module_cpp.py** (2): All 7 tools found, all missing
- **test_module_git.py** (4): Found/missing, config set/missing
- **test_module_node.py** (3): Found, node missing, tsc missing
- **test_module_nvim.py** (3): Found, all missing, fd-only-as-fdfind
- **test_module_python.py** (3): Found, missing, venv available
- **test_module_vscode.py** (3): Found with WSL extension, code missing, WSL extension missing

### Profiles (9 tests)
- **test_profiles.py** (9): Field validation, registry count, profile contents (C++, Python), dry-run, apt install args, failure handling, subprocess exceptions

### Resolver (6 tests)
- **test_resolver.py** (6): No-deps ordering, dependency ordering, multi-deps, circular detection, unknown dependency skipping, diamond resolution

### Shell Utilities (8 tests)
- **test_shell.py** (8): run_command pass-through/with_cwd/check_raises, which found/not_found, apt install success/failure/timeout

### Snapshot (12 tests)
- **test_snapshot.py** (12): Capture returns snapshot + timestamp, storage sanitize/save/load/list/not_found, diff (added/removed packages, env vars, config changes, no changes)

---

## Coverage Details

| Module | Statements | Missed | Coverage |
|--------|-----------|--------|----------|
| `ai/base.py` | 19 | 0 | 100% |
| `ai/factory.py` | 40 | 4 | 90% |
| `ai/providers/openai.py` | 55 | 2 | 96% |
| `ai/client.py` | 27 | 11 | 59% |
| `ai/context.py` | 66 | 26 | 61% |
| `ai/providers/ollama.py` | 53 | 33 | 38% |
| `ai/providers/anthropic.py` | 50 | 34 | 32% |
| `ai/providers/gemini.py` | 55 | 39 | 29% |
| `cli/main.py` | 364 | 364 | 0% |
| `config/manager.py` | 39 | 1 | 97% |
| `doctor/fixes.py` | 24 | 4 | 83% |
| `doctor/runner.py` | 102 | 52 | 49% |
| `inspector/checker.py` | 7 | 0 | 100% |
| `inspector/detector.py` | 54 | 7 | 87% |
| `inspector/installer.py` | 15 | 2 | 87% |
| `logging/logger.py` | 16 | 16 | 0% |
| `modules/base.py` | 17 | 0 | 100% |
| `modules/resolver.py` | 25 | 0 | 100% |
| `modules/vscode/module.py` | 31 | 8 | 74% |
| `modules/nvim/module.py` | 54 | 25 | 54% |
| `modules/cpp/module.py` | 62 | 29 | 53% |
| `modules/python/module.py` | 52 | 25 | 52% |
| `modules/node/module.py` | 57 | 29 | 49% |
| `modules/git/module.py` | 53 | 29 | 45% |
| `profiles/definitions.py` | 11 | 0 | 100% |
| `profiles/installer.py` | 59 | 23 | 61% |
| `snapshot/diff.py` | 27 | 0 | 100% |
| `snapshot/storage.py` | 45 | 2 | 96% |
| `snapshot/capture.py` | 108 | 76 | 30% |
| `snapshot/restore.py` | 55 | 55 | 0% |
| `utils/shell.py` | 14 | 0 | 100% |
| **TOTAL** | **1660** | **896** | **46.02%** |

---

## Warnings

- `google.generativeai` is deprecated. The Gemini provider should be migrated to `google.genai`.  
  See: https://github.com/google-gemini/deprecated-generative-ai-python

---

## CI Pipeline Status (GitHub Actions)

| Job | Status |
|-----|--------|
| Lint (Ruff) | ✅ Pass |
| Type Check (Mypy) | ✅ Pass |
| Tests (Pytest + Coverage) | ✅ Pass |
| Build Verification | ✅ Configured |

---

## Files Check Report

| Check | Result |
|-------|--------|
| AI-generated files committed | None (`.commandcode/` gitignored and removed from tracking) |
| `.env` exposed | No (gitignored) |
| VHS artifacts committed | No (`.gif`, `.mp4`, `.log` gitignored) |
| `test.tape` committed | No (gitignored) |
| `tutorial.tape` | Tracked (demo tape for documentation) |
| Build artifacts | Gitignored (`dist/`, `build/`, `*.egg-info/`) |
| Coverage files | Gitignored (`.coverage`, `coverage.xml`, `htmlcov/`) |
