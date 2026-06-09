# DevPilot Deep Dive — Exhaustive Walkthrough

This document explains how every component of DevPilot works internally. After reading this, you will understand the full lifecycle of every command, the rationale behind every design choice, how to debug issues, and how to extend DevPilot with new modules.

---

## Table of Contents

1. [How `devpilot setup` Works](#1-how-devpilot-setup-works)
2. [How `devpilot doctor` Works](#2-how-devpilot-doctor-works)
3. [How `devpilot info` Works](#3-how-devpilot-info-works)
4. [How `devpilot init` Works](#4-how-devpilot-init-works)
5. [The BaseModule Contract](#5-the-basemodule-contract)
6. [Module Deep Dives](#6-module-deep-dives)
   - [Git Module](#git-module)
   - [Python Module](#python-module)
   - [Node Module](#node-module)
   - [C/C++ Module](#cc-module)
   - [VS Code Module](#vs-code-module)
   - [Neovim Module](#neovim-module)
7. [Shell Utilities Safety Model](#7-shell-utilities-safety-model)
8. [Config Manager Internals](#8-config-manager-internals)
9. [Logging Internals](#9-logging-internals)
10. [Test Architecture & Mocking Strategy](#10-test-architecture--mocking-strategy)
11. [CI Pipeline Design](#11-ci-pipeline-design)
12. [How to Add a New Module](#12-how-to-add-a-new-module)
13. [Common Issues & Debugging](#13-common-issues--debugging)

---

## 1. How `devpilot setup` Works

### Entrypoint

The user runs `devpilot setup` or `devpilot setup <module_name>`. The Typer app dispatches to `setup()` in `cli/main.py`.

### Module Selection

```python
ALL_MODULES = {
    "git": GitModule,
    "python": PythonModule,
    "node": NodeModule,
    "cpp": CppModule,
    "vscode": VSCodeModule,
    "nvim": NvimModule,
}

INSTALL_ORDER = ["git", "python", "node", "cpp", "vscode", "nvim"]
```

If no argument is given, `target_modules = INSTALL_ORDER`. If a specific module is named, `target_modules = [module_name]` and the name is validated against `ALL_MODULES` keys.

### Progress Bar

A `rich.progress.Progress` context manager creates a bar with description text, a progress bar, and a tick column. The task starts at 0 and advances by 1 after each module.

### Install Loop

For each module name in `target_modules`:

1. **Update progress description** to `"Setting up {name}..."` so the user sees real-time feedback.
2. **Instantiate the module class** — `ALL_MODULES[name]()` creates a new instance.
3. **Call `module.install()`** — this is the core work. Returns `True` on success, `False` on failure.
4. **On success**: Call `config_manager.mark_installed(name)` which writes to `~/.config/devpilot/config.yaml`.
5. **On failure (`return False`)**: Append name to `failed` list, show a yellow warning.
6. **On exception**: Catch `Exception`, log the full traceback via `logger.exception()`, append to `failed`, show a red error.

### Final Summary

After the loop, if `failed` is non-empty, print a yellow message listing failed modules. Otherwise print green success.

### Why This Order?

```
git → python → node → cpp → vscode → nvim
```

- **git** first because it has zero dependencies and is a prerequisite for cloning/lazy.nvim bootstrapping.
- **python** second because it's lightweight and needed for pip/pipx workflows.
- **node** third because it's a dependency of nvim's Mason and nvim-cmp plugins.
- **cpp** fourth because it's the heaviest install and self-contained.
- **vscode** fifth because it's a detection-only module (no actual install).
- **nvim** last because it depends on node being present for LSP and completion.

---

## 2. How `devpilot doctor` Works

### Flow

```
devpilot doctor
  → doctor() in cli/main.py
    → creates all 6 module instances
    → calls run_all_doctors(modules) from doctor/runner.py
    → renders results in Rich table
    → computes and displays health score in Rich panel
```

### `run_all_doctors()` Internals

```python
def run_all_doctors(modules: list[BaseModule]) -> tuple[list[CheckResult], int]:
    all_results: list[CheckResult] = []
    for module in modules:
        all_results.extend(module.doctor())

    total = len(all_results)
    passed = sum(1 for r in all_results if r.passed)

    health_score = round((passed / total) * 100) if total > 0 else 100
    return all_results, health_score
```

1. Iterates every module, calling `module.doctor()`.
2. Flattens all `CheckResult` objects into one list.
3. Counts total checks and passed checks.
4. Health score = `round((passed / total) * 100)`. If there are zero checks (shouldn't happen), score is 100.
5. Returns the flat list and the integer score.

### Rendering

Each `CheckResult` is rendered as a table row:

| Status | Check Name         | Message              | Fix                    |
| ------ | ------------------ | -------------------- | ---------------------- |
| ✅      | git installed      | git version 2.43.0   |                        |
| ❌      | git user.name      | Not set.             | `git config --global...` |

The health score panel uses:
- **Green** (≥90): healthy environment
- **Yellow** (60-89): some issues need attention
- **Red** (<60): significant problems

### Why `doctor()` Is Separate from `verify()`

- **`verify()`** is designed to run after `install()` for quick post-install sanity checks.
- **`doctor()`** is designed for ongoing health monitoring — it might include deeper checks like network tests, filesystem permissions, or config validation.

For simple modules (git, python, node, cpp, vscode, nvim), `doctor()` delegates to `verify()`. This is the simplest correct implementation. A module can override `doctor()` independently later without changing its `verify()` logic.

---

## 3. How `devpilot info` Works

### `_get_system_info()` function

This is an inline function (not a class) in `cli/main.py`. It collects 6 data points:

#### Ubuntu Version
```python
run_command(["lsb_release", "-d"], capture=True, check=False)
```
Parses the "Description:" line from stdout. Falls back to "Unknown".

#### Kernel Version
```python
run_command(["uname", "-r"], capture=True, check=False)
```
Direct stdout strip. Falls back to "Unknown".

#### WSL Version
```python
Path("/proc/version").read_text(encoding="utf-8")
```
Checks for the substrings `"icrosoft"` or `"WSL"` in `/proc/version`. If found, checks the kernel version prefix to distinguish WSL1 (kernel 3.x/4.4.0) from WSL2 (kernel 5.x+). If neither marker is present, reports "Not WSL".

#### CPU Cores
```python
run_command(["nproc"], capture=True, check=False)
```
Stdout strip. Falls back to "Unknown".

#### RAM
```python
Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
```
Finds the line starting with `"MemTotal:"`, parses the KB value, converts to GB with one decimal place.

#### Disk
```python
run_command(["df", "-h", "/"], capture=True, check=False)
```
Parses the second line of output (first is headers). Extracts size, used, available, and usage percentage columns.

### Rendering

A `Rich Table` with `show_header=False`, two columns styled in cyan (property) and green (value). Each key-value pair from the dictionary becomes a row.

### Error Handling

Every data point is wrapped in try/except. If any single reading fails, that field shows "Unknown" rather than crashing the entire command.

---

## 4. How `devpilot init` Works

### Template Validation

```python
allowed = {"cpp", "python", "cli"}
```

If the template name isn't in `allowed`, prints available options and exits with code 1.

### Directory Safety

Checks if `Path.cwd() / project_name` already exists. If it does, prints an error and exits — we never overwrite existing directories.

### Template Dispatch

```python
if template == "cpp":
    _scaffold_cpp(project_dir, project_name)
elif template == "python":
    _scaffold_python(project_dir, project_name, cli=False)
elif template == "cli":
    _scaffold_python(project_dir, project_name, cli=True)
```

### C++ Template (`_scaffold_cpp`)

Creates:
```
my-cpp-project/
├── CMakeLists.txt          # C++17, project(my-cpp-project)
├── src/
│   └── main.cpp             # Hello world
└── .gitignore               # build/, *.out, *.o
```

The `CMakeLists.txt` sets `CMAKE_CXX_STANDARD 17` and `CMAKE_CXX_STANDARD_REQUIRED ON`.

### Python Template (`_scaffold_python`, `cli=False`)

Creates:
```
my-project/
├── pyproject.toml           # hatchling build, no CLI deps
├── README.md
├── src/
│   └── my_project/
│       ├── __init__.py
│       └── main.py          # def main(): print("Hello...")
├── tests/
│   ├── __init__.py
│   └── test_main.py         # imports and calls main()
└── .gitignore
```

### CLI Template (`_scaffold_python`, `cli=True`)

Same as Python but:
- `pyproject.toml` adds `typer[all]>=0.15` as a dependency and a `[project.scripts]` entrypoint.
- `main.py` uses Typer with `@app.command()` decorator for a `hello` command instead of a plain `main()` function.

---

## 5. The BaseModule Contract

### Abstract Base Class

```python
class BaseModule(ABC):
    name: str

    @abstractmethod
    def install(self) -> bool: ...
    @abstractmethod
    def verify(self) -> list[CheckResult]: ...
    @abstractmethod
    def doctor(self) -> list[CheckResult]: ...
```

Every module must:

1. **Set `name`** as a class attribute (e.g., `name: str = "git"`).
2. **Implement `install()`** — performs the actual tool installation and configuration. Returns `True` if installation succeeded (tools are usable), `False` otherwise. Should be idempotent (safe to run twice).
3. **Implement `verify()`** — runs quick post-install checks using only CLI commands. Returns a list of `CheckResult` objects. No interactive input.
4. **Implement `doctor()`** — runs comprehensive health checks. Can delegate to `verify()` or add deeper checks.

### CheckResult Dataclass

```python
@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    message: str
    fix: str | None = None
```

- **`name`**: Human-readable identifier like `"git installed"`.
- **`passed`**: `True` if the tool/config is healthy.
- **`message`**: Descriptive text, e.g., version string or error description.
- **`fix`**: CLI command or instruction the user can run to resolve the issue. `None` if the check passed.

### Module Isolation Rule

**Modules must not import from each other.** The only shared dependencies are:
- `devpilot.modules.base` — for `BaseModule` and `CheckResult`
- `devpilot.utils.shell` — for `run_command()`, `which()`, `apt_install()`

This rule means:
- Each module is independently testable.
- Removing a module requires deleting one directory — no ripple effects.
- Adding a module has zero impact on existing modules.
- CI tests for different modules can run in parallel.

---

## 6. Module Deep Dives

### Git Module

**File**: `src/devpilot/modules/git/module.py`

**Class**: `GitModule(BaseModule)`, `name = "git"`

#### `install()`
1. Checks `which("git")`. If not found, runs `apt_install(["git"])`.
2. Verifies git is now in PATH. Returns `False` if still missing.
3. Calls `_get_git_config("user.name")` to check if global user.name is set.
4. If empty, **prompts the user interactively** with `input()` for their name. This is the only module that uses interactive input.
5. If the user provides a name, runs `git config --global user.name <name>`.
6. Repeats steps 3-5 for `user.email`.
7. Returns `True` if git exists and config is handled. Non-fatal if user skips the prompt (handles `EOFError`/`KeyboardInterrupt`).

#### `verify()`
Returns 3 checks:
1. `"git installed"` — runs `git --version`, passes if found in PATH.
2. `"git user.name"` — passes if `git config --global user.name` returns a non-empty value.
3. `"git user.email"` — passes if `git config --global user.email` returns a non-empty value.

Each failed check provides a `fix` string with the exact `git config` command to run.

#### `doctor()`
Delegates to `verify()`. The module is simple enough that the same checks serve both purposes.

#### `_get_git_config(key)`
Helper that runs `git config --global <key>`, returns the stripped stdout or empty string. Handles the case where `returncode != 0` (config key not set).

### Python Module

**File**: `src/devpilot/modules/python/module.py`

**Class**: `PythonModule(BaseModule)`, `name = "python"`

#### `install()`
1. Checks `which("python3")` and `which("pip3")`. If either missing, runs `apt_install(["python3", "python3-pip", "python3-venv"])`.
2. Verifies `python3` is now in PATH. Returns `False` if not.
3. **Smoke test**: Creates a temporary directory with `tempfile.mkdtemp()`. Inside it:
   - Runs `python3 -m venv .venv` to create a virtual environment.
   - Runs `.venv/bin/pip install rich` to install a real package.
   - Runs `.venv/bin/python -c "import rich; print('ok')"` to verify the import works.
   - Cleans up the temp directory with `shutil.rmtree()` in a `finally` block.
4. Returns `True`. Smoke-test failures are logged as warnings but don't cause `install()` to return `False` — the core toolchain is installed.

#### `verify()`
Returns 3 checks:
1. `"python3 installed"` — runs `python3 --version`.
2. `"pip installed"` — runs `pip3 --version`, parses out the version (strips the parenthetical `(python 3.12)` suffix).
3. `"venv module"` — runs `python3 -m venv --help` and checks `returncode == 0`.

#### `doctor()`
Delegates to `verify()`.

### Node Module

**File**: `src/devpilot/modules/node/module.py`

**Class**: `NodeModule(BaseModule)`, `name = "node"`

#### `install()`
1. Checks `which("node")`. If not found:
   - Runs `sudo apt-get update`.
   - Runs `curl -fsSL https://deb.nodesource.com/setup_lts.x` to fetch the NodeSource setup script.
   - If curl fails (non-zero return code), returns `False`.
   - Writes the script to a temporary file (using `tempfile.NamedTemporaryFile`), executes it with `sudo bash <script>`, and cleans up the temp file in a `finally` block.
   - Runs `apt_install(["nodejs"])` to install Node.js from the newly added repository.
2. Verifies `node` is now in PATH. Returns `False` if not.
3. Checks `which("tsc")`. If TypeScript is not installed:
   - Runs `sudo npm install -g typescript` with a 300s timeout.
   - Warns if it fails (non-fatal — Node.js itself is installed).
4. Returns `True`.

#### `verify()`
Returns 3 checks:
1. `"node installed"` — runs `node --version`.
2. `"npm installed"` — runs `npm --version`.
3. `"TypeScript installed"` — checks `which("tsc")`.

#### `doctor()`
Delegates to `verify()`.

### C/C++ Module

**File**: `src/devpilot/modules/cpp/module.py`

**Class**: `CppModule(BaseModule)`, `name = "cpp"`

#### `install()`
1. Runs `apt_install(["build-essential", "gcc", "g++", "clang", "cmake", "gdb", "make"])`.
2. Verifies `g++` is now in PATH. Returns `False` if not.
3. **Smoke test**: Creates a temp directory, writes a `hello.cpp`:
   ```cpp
   #include <iostream>
   int main() { std::cout << "Hello from DevPilot" << std::endl; return 0; }
   ```
   Compiles with `g++ -std=c++17 hello.cpp -o hello`.
   Runs `./hello` and checks that stdout contains `"Hello from DevPilot"`.
   Cleans up temp directory in `finally`.
4. Returns `True` if compile + run both succeed.

#### `verify()`
Returns 7 checks:
1. `"gcc installed"` — `gcc --version`
2. `"g++ installed"` — `g++ --version`
3. `"clang installed"` — `clang --version`
4. `"cmake installed"` — `cmake --version`
5. `"gdb installed"` — `gdb --version`
6. `"make installed"` — `make --version`
7. `"g++ can compile"` — quick compile test: write `int main() { return 0; }` to a temp file, compile with `g++ -std=c++17`, check return code. Uses `mkdtemp` + `rmtree` for cleanup.

Each version check extracts the first line of stdout for the message.

#### `doctor()`
Delegates to `verify()`.

### VS Code Module

**File**: `src/devpilot/modules/vscode/module.py`

**Class**: `VSCodeModule(BaseModule)`, `name = "vscode"`

#### `install()`
This is a **detection-only module**. It does not install VS Code (VS Code must be installed on Windows). It:
1. Checks `which("code")` to see if the VS Code CLI server is available in WSL2.
2. If found, logs the path and returns `True`.
3. If not found, logs a warning message explaining that VS Code must be installed on Windows and launched from WSL2. Returns `False`.

#### `verify()`
Returns 2 checks:
1. `"VS Code CLI"` — runs `code --version`, passes if `which("code")` succeeds.
2. `"WSL extension"` — runs `code --list-extensions` and greps for `"ms-vscode-remote.remote-wsl"`. Passes if the extension ID appears in the output. If `code` itself is missing, the check fails with a message saying we can't check without the CLI.

#### `doctor()`
Delegates to `verify()`.

### Neovim Module

**File**: `src/devpilot/modules/nvim/module.py`

**Class**: `NvimModule(BaseModule)`, `name = "nvim"`

This is the most complex module. It installs Neovim plus companion tools, deploys a full `init.lua` configuration with lazy.nvim plugin management, and runs headless plugin sync and health checks.

#### `install()`
1. Runs `apt_install(["neovim", "ripgrep", "fd-find"])`.
2. Verifies `which("nvim")` exists. Returns `False` if not.
3. **`fd` symlink**: Ubuntu's `fd-find` package installs the binary as `fdfind`. If `fdfind` is found but `fd` is not, creates a symlink: `sudo ln -sf $(which fdfind) /usr/local/bin/fd`. This ensures Telescope's `fd` dependency works.
4. **Deploy config**: Calls `_deploy_config()` which writes the full `INIT_LUA_CONTENT` (a 379-line string constant) to `~/.config/nvim/init.lua`. Creates the parent directory if needed.
5. **Headless Lazy sync**: Runs `nvim --headless "+Lazy! sync" +qa` with a 600s timeout. This downloads and installs all plugins defined in the init.lua. Warns if return code is non-zero.
6. **Headless checkhealth**: Runs `nvim --headless "+checkhealth" +qa` with a 120s timeout. Logs pass/fail.
7. Returns `True`.

#### Plugin Stack (what the init.lua configures)

| Plugin                    | Purpose                                              |
| ------------------------- | ---------------------------------------------------- |
| `lazy.nvim`               | Plugin manager, bootstraps itself if missing         |
| `telescope.nvim`          | Fuzzy finder (files, grep, buffers, help tags)       |
| `nvim-treesitter`         | Syntax highlighting and indentation                  |
| `mason.nvim`              | LSP/DAP/linter installer                             |
| `mason-lspconfig.nvim`    | Bridges mason ↔ lspconfig                            |
| `nvim-lspconfig`          | LSP client configuration                             |
| `nvim-cmp`                | Autocompletion engine                                |
| `gitsigns.nvim`           | Git gutter indicators                                |

#### Keymaps Configured

| Keymap       | Action                        |
| ------------ | ----------------------------- |
| `<Space> ff` | Telescope find files          |
| `<Space> fg` | Telescope live grep           |
| `<Space> fb` | Telescope buffers             |
| `<Space> fh` | Telescope help tags           |
| `<Space> e`  | Open diagnostic float         |
| `[d` / `]d`  | Previous/next diagnostic      |
| `gd`         | Go to definition              |
| `K`          | Hover documentation           |
| `gi`         | Go to implementation          |
| `gr`         | Find references               |
| `<Space> rn` | Rename symbol                 |
| `<Space> ca` | Code action                   |

#### `verify()`
Returns 4 checks:
1. `"neovim installed"` — `nvim --version`, parses first line.
2. `"ripgrep installed"` — checks `which("rg")`.
3. `"fd-find installed"` — checks `which("fd") or which("fdfind")`.
4. `"nvim config deployed"` — checks `Path("~/.config/nvim/init.lua").exists()`.

#### `doctor()`
Delegates to `verify()`.

---

## 7. Shell Utilities Safety Model

### `run_command()`

```python
def run_command(
    cmd: list[str],
    capture: bool = True,
    check: bool = False,
    timeout: int = 300,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
```

This is the **only function in the entire codebase that spawns subprocesses**. Every shell interaction goes through it.

#### Safety Properties

1. **No `shell=True`**. Commands are passed as `list[str]` — each argument is a separate string. This eliminates shell injection entirely. You cannot inject `; rm -rf /` because the shell never interprets the command string.

2. **Text mode**. `capture_output=True, text=True` means stdout/stderr are `str` (not `bytes`). No decoding needed.

3. **Timeout**. Default 300 seconds. Prevents hanging processes from blocking the CLI. Callers can override with higher timeouts for slow operations (e.g., `apt_install` uses 600s, `Lazy sync` uses 600s).

4. **Explicit error handling**. `check=False` by default means callers must inspect `result.returncode` themselves. This avoids unexpected crashes. Set `check=True` when you want the function to raise `CalledProcessError` on failure.

5. **cwd as string**. The `cwd` parameter accepts a `Path` but converts it to `str` before passing to `subprocess.run`. This avoids type issues with older subprocess APIs.

### `which()`

```python
def which(program: str) -> Path | None:
```

Wraps `shutil.which()`. Returns a `Path` object if the program is found in PATH, `None` otherwise. This is the canonical way modules check for tool availability.

### `apt_install()`

```python
def apt_install(packages: list[str]) -> bool:
```

Runs `sudo apt-get install -y <packages...>`. Wraps the call in try/except for `TimeoutExpired`, `OSError`, and `FileNotFoundError`. Returns `True` if `returncode == 0`, `False` otherwise.

Note: `sudo` is required because apt needs root. This is safe because the command arguments are a list (no shell injection) and the user explicitly ran `devpilot setup` expecting system changes.

---

## 8. Config Manager Internals

### File Location

```
~/.config/devpilot/config.yaml
```

### Schema

```yaml
installed_modules:
  - git
  - python
  - node
preferences:
  default_editor: code
  default_shell: bash
  auto_update: "true"
```

### `load()` Flow

1. Check if `self.config_path.exists()`. If not, return `{"installed_modules": [], "preferences": {}}`.
2. Read the file text.
3. Parse with `yaml.safe_load()`.
4. If the result is not a dict (e.g., the file contains a bare string or list), return defaults.
5. Ensure both `"installed_modules"` and `"preferences"` keys exist (use `dict.setdefault()`).
6. Return the dict.

**Corrupted YAML**: `yaml.safe_load()` raises `YAMLError`. The `except` clause catches both `YAMLError` and `OSError` and returns defaults. The file is never deleted automatically — the user can fix it manually or delete it.

### `save()` Flow

1. Create parent directories with `mkdir(parents=True, exist_ok=True)`.
2. Serialize with `yaml.safe_dump(data, default_flow_style=False)` — uses block style (not flow style).
3. Write to file.

### `mark_installed()` Flow

1. Load current config.
2. Get or create the `"installed_modules"` list.
3. Append the module name if not already present (prevents duplicates).
4. Save.

### `get_preference()` / `set_preference()` Flow

- `get_preference(key, default)` loads config, gets `preferences[key]`, returns as string. Falls back to `default`.
- `set_preference(key, value)` loads config, sets `preferences[key] = value`, saves.

---

## 9. Logging Internals

### File Location

```
~/.local/share/devpilot/logs/devpilot.log
```

### Log Format

```
[2024-01-15 14:30:00][INFO][git] git installed successfully.
[2024-01-15 14:30:05][ERROR][node] Failed to fetch NodeSource setup script.
```

Format string: `"[%(asctime)s][%(levelname)s][%(module)s] %(message)s"`

Date format: `"%Y-%m-%d %H:%M:%S"`

### Rotation

Uses `logging.handlers.TimedRotatingFileHandler`:
- **`when="midnight"`**: Rotation happens at midnight each day.
- **`interval=1`**: One rotation per interval (daily).
- **`backupCount=7`**: Keeps 7 days of logs. Oldest log is deleted when an 8th file would be created.

Rotated files are named `devpilot.log.YYYY-MM-DD`.

### Logger Setup (`setup_logger()`)

```python
def setup_logger(name: str = "devpilot") -> logging.Logger:
```

1. Creates `LOG_DIR` (`~/.local/share/devpilot/logs/`) if it doesn't exist.
2. Gets or creates a logger with the given name.
3. Sets level to `DEBUG` (captures everything).
4. If the logger already has handlers (idempotency check), returns immediately.
5. Creates a `TimedRotatingFileHandler`, sets level to `DEBUG`, attaches the formatter.
6. Returns the logger.

### Usage in Modules

Each module gets a logger with:
```python
logger = logging.getLogger("devpilot")
```

Log levels used:
- **`logger.info()`** — normal operations (tool installed, config deployed).
- **`logger.warning()`** — soft failures (optional component missing, retryable error).
- **`logger.error()`** — hard failures (tool not found, installation failed).
- **`logger.exception()`** — unhandled exceptions (captures full traceback).

---

## 10. Test Architecture & Mocking Strategy

### Philosophy

Tests verify **logic**, not side effects. Every test file mocks `subprocess.run`, `shutil.which`, and filesystem operations. No test requires actual tools to be installed.

### Test Structure

```
tests/
├── conftest.py             ← shared fixtures
├── test_config_manager.py  ← 6 tests for ConfigManager
├── test_doctor_runner.py   ← 5 tests for health score logic
├── test_shell.py           ← 8 tests for shell utilities
├── test_module_git.py      ← 4 tests for GitModule.verify()
├── test_module_python.py   ← 3 tests for PythonModule.verify()
├── test_module_node.py     ← 3 tests for NodeModule.verify()
├── test_module_cpp.py      ← 2 tests for CppModule.verify()
├── test_module_vscode.py   ← 3 tests for VSCodeModule.verify()
└── test_module_nvim.py     ← 3 tests for NvimModule.verify()
```

### Shared Fixtures (`conftest.py`)

- **`temp_config_dir`**: Uses pytest's `tmp_path` fixture to create an isolated config directory.
- **`config_manager`**: Creates a `ConfigManager` pointed at a temp path — no real config is touched.
- **`mock_run_command`**: A plain `MagicMock` for quick tests.
- **`mock_subprocess_run`**: Another `MagicMock` (less used, exists for flexibility).

### Mocking Strategy

Every test follows the same pattern:

1. **Mock `which()`** with `patch("devpilot.modules.<module>.module.which")` to control which tools appear installed.
2. **Mock `run_command()`** with `patch("devpilot.modules.<module>.module.run_command")` to simulate version outputs and command results.
3. **Mock filesystem paths** (like `INIT_LUA_PATH.exists()`) with `patch` to control config file presence.
4. **Call `module.verify()`** and assert on the returned `CheckResult` list.

**Key rule**: Tests use `patch()` on the module's own import of these functions, not on the source. This is the `patch("devpilot.modules.git.module.which")` pattern — patching where the function is *used*, not where it's *defined*.

### Test Coverage Summary

| Test file                | What it validates                                           |
| ------------------------ | ----------------------------------------------------------- |
| `test_config_manager.py` | Load defaults, save/load roundtrip, mark_installed dedup, get/set preferences, corrupted YAML fallback |
| `test_doctor_runner.py`  | Health score: all-passing=100, all-failing=0, mixed=50, empty=100, single mixed=50 |
| `test_shell.py`          | run_command args passthrough, cwd handling, check=True raises, which found/not_found, apt_install success/failure/timeout |
| `test_module_git.py`     | Verify git found with version, git missing, config set, config missing |
| `test_module_python.py`  | Verify python found with version, python missing, venv available |
| `test_module_node.py`    | Verify node/npm/tsc all found, node missing, tsc missing |
| `test_module_cpp.py`     | Verify all 7 tools found and pass, all 6 tools missing |
| `test_module_vscode.py`  | Verify code found + WSL extension, code missing, WSL extension missing |
| `test_module_nvim.py`    | Verify all 4 checks pass, all missing, fd only as fdfind |

---

## 11. CI Pipeline Design

### Trigger

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

Runs on every push to `main` and every PR targeting `main`.

### Job: `lint-typecheck-test`

Runs on `ubuntu-24.04`. Steps:

1. **Checkout** — `actions/checkout@v4`.
2. **Set up Python 3.12** — `actions/setup-python@v5`.
3. **Install dependencies** — `pip install -e ".[dev]"` installs the package in editable mode with all dev dependencies (pytest, ruff, black, mypy).
4. **Ruff check** — `ruff check src/ tests/` — zero tolerance for lint errors.
5. **Black check** — `black --check src/ tests/` — fails if any file is not formatted.
6. **Mypy type check** — `mypy src/` — strict mode, fails on any type error.
7. **Pytest** — `pytest -v` — runs all 37 tests.

### Why This Order

Lint and format first (fast feedback), then type checking (catches logic errors), then tests last (since tests won't pass if types are wrong).

---

## 12. How to Add a New Module

### Step-by-Step Guide

1. **Create the module directory**
   ```
   src/devpilot/modules/<name>/
   ├── __init__.py
   └── module.py
   ```

2. **Implement the module class**
   ```python
   import logging
   from devpilot.modules.base import BaseModule, CheckResult
   from devpilot.utils.shell import apt_install, run_command, which

   logger = logging.getLogger("devpilot")

   class MyModule(BaseModule):
       name: str = "my-tool"

       def install(self) -> bool:
           # Install your tool here
           # Use apt_install() for apt packages
           # Use run_command() for custom scripts
           # Return True on success, False on failure
           ...

       def verify(self) -> list[CheckResult]:
           # Return at least one CheckResult
           ...

       def doctor(self) -> list[CheckResult]:
           return self.verify()
   ```

3. **Register in `cli/main.py`**
   ```python
   from devpilot.modules.my.module import MyModule

   ALL_MODULES = {
       ...
       "my-tool": MyModule,
   }

   INSTALL_ORDER = [..., "my-tool"]
   ```

4. **Write tests**
   ```
   tests/test_module_my.py
   ```
   Mock `which()` and `run_command()`, call `module.verify()`, assert on results.

5. **Run full validation**
   ```bash
   ruff check src/ tests/
   black --check src/ tests/
   mypy src/
   pytest -v
   ```

### Rules to Follow

- **No cross-module imports**. Only import from `base` and `utils/shell`.
- **Type hints on everything**. Every function must have parameter and return type annotations.
- **Docstrings on public functions**. Every public method needs a docstring with Args/Returns.
- **No bare `except:`**. Always catch specific exceptions.
- **Use `pathlib.Path`**. Never use string paths.
- **Use `run_command()`**. Never call `subprocess` directly.
- **Use Rich for output in install()**. Modules can use `logging` for debug info, but any user-facing messages during install should use the `rich.console.Console`.

---

## 13. Common Issues & Debugging

### "Module X not found in PATH"

Run `devpilot doctor` to see which specific checks failed. The doctor output includes exact `fix` commands.

### "apt_install hangs"

apt may be waiting for a lock. Check:
```bash
sudo lsof /var/lib/dpkg/lock-frontend
```
If another process holds the lock, wait for it or kill it.

### "Lazy sync failed"

The headless Neovim sync may fail if:
- git is not installed (install git first: `devpilot setup git`)
- node is not installed (install node first: `devpilot setup node`)
- Network issues (the sync downloads many plugins from GitHub)

Re-run: `devpilot setup nvim` or manually: `nvim --headless "+Lazy! sync" +qa`

### "Logs are not being written"

Check that `~/.local/share/devpilot/logs/` exists and is writable:
```bash
ls -la ~/.local/share/devpilot/logs/
```

### "Config file corrupted"

Delete it and let `devpilot setup` recreate it:
```bash
rm ~/.config/devpilot/config.yaml
```

### "Tests fail with import errors"

Make sure you installed in dev mode:
```bash
pip install -e ".[dev]"
```

### "mypy reports errors"

Common causes:
- Missing type annotation on a function parameter or return value.
- Using a nullable value without checking for `None`.
- Incorrect import (importing module instead of from module import Class).

Fix the type errors — the CI enforces strict mode with zero tolerance.
