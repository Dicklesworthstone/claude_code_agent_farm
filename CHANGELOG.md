# Changelog

All notable changes to Claude Code Agent Farm are documented in this file.

This project has no tagged releases or GitHub releases. Changes are organized
chronologically by the date they landed on `main`, grouped into logical
development phases. Each entry links to the actual commit on GitHub.

Repository: <https://github.com/Dicklesworthstone/claude_code_agent_farm>

---

## 2026-02-22 — License and branding update

### Changed

- Updated license from plain MIT to **MIT + OpenAI/Anthropic Rider**, restricting
  use by OpenAI, Anthropic, and their affiliates without express written
  permission.
  ([`66647df`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/66647df11ba94102ab88c9a03afdc41f87db6f11))
  ([`f6c0bb3`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/f6c0bb358b70a5d90059d6eb32f24258aad783cc))

### Added

- GitHub social preview image (1280x640) for link previews.
  ([`dee3271`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/dee32719b58a78fb47b3b33bb0fa00e7775f08c3))

---

## 2025-09-25 — Next.js useEffect guidelines

### Changed

- Updated Next.js 15 best practices guide with guidelines for using React
  `useEffect` alongside TanStack Query and Zustand.
  ([`ed68548`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/ed6854825e413459f20a2eabc27342150959448b))

---

## 2025-07-19 — FastMCP best practices guide

### Added

- New **Python FastMCP Best Practices** guide
  (`best_practices_guides/PYTHON_FASTMCP_BEST_PRACTICES.md`).
  ([`1e50891`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/1e508915bab610ac37bf2edf694672cdb1b9b03b))

---

## 2025-07-06 — Reliability and context-clearing improvements

### Changed

- `needs_restart()` now returns a reason string (`"context"`, `"error"`,
  `"idle"`) instead of a boolean, enabling differentiated recovery: low-context
  agents receive `/clear` instead of a full restart, avoiding settings races.
- New `clear_agent_context()` method sends `/clear` and re-injects the working
  prompt without restarting Claude Code.
- Active shell-prompt probe: after 3 seconds of passive detection, an `echo`
  with a unique marker is sent to the pane to positively confirm shell readiness,
  accommodating minimal or custom prompts.
- Context-reset macro changed from `/reset` to `/clear` (Ctrl+R broadcast).
- Default agent count reduced from 20 to 6 for safer defaults.
- DSPy best practices guide condensed and restructured.
  ([`6d731f3`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/6d731f31d5642e1c21ffe2c898fa8fb7acf409a8))

---

## 2025-07-02 — 2025-07-03 — Huge prompt support, content guides, and .gitignore management

### Added

- **Huge prompt support**: `tmux_send()` now uses the tmux buffer API
  (`load-buffer` / `paste-buffer`) with a temp file for payloads that exceed
  shell-quoting limits, making arbitrarily large prompts safe.
  ([`fdcfa48`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/fdcfa4865a6951e7cead2e6c313cccf66e87f177))
- **Automatic `.gitignore` management**: `_ensure_gitignore_entries()` adds
  patterns for `.heartbeats/`, state files, backup directories, and HTML
  reports to the target project's `.gitignore` (idempotent, creates file if
  missing).
  ([`1bd15bd`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/1bd15bd536f87329266e9feaa8157088d3aa78cc))
- **DSPy and Python LLM Pipeline Best Practices** guide (3,400+ lines).
  ([`b3f0223`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b3f0223be4c7363fd6dc6bda3e45726845e8f1eb))

### Changed

- Updated PostgreSQL 17 & Python best practices guide with expanded content.
  ([`a92a0bb`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/a92a0bbcd023dcc6227209f11608472c8036a71f))

---

## 2025-07-01 — 2025-07-02 — Coordinating agents, major monitoring upgrades, and HTML reports

### Orchestration and monitoring

- **Adaptive idle timeout**: tracks cycle-completion times across all agents and
  sets timeout to 3x the median cycle time (bounded 30s -- 600s), preventing
  false positives on complex tasks and speeding detection on simple ones.
  ([`b4f211d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b4f211d4269ef8c0c942511804e22730475bea7e))
- **Double Ctrl+C force-kill**: first Ctrl+C triggers graceful shutdown; a
  second within 3 seconds force-kills the tmux session and exits immediately.
  ([`b4f211d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b4f211d4269ef8c0c942511804e22730475bea7e))
- **Size-based backup rotation**: `_cleanup_old_backups()` now enforces a 200 MB
  total-size limit in addition to a count limit, preventing disk bloat.
  ([`b4f211d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b4f211d4269ef8c0c942511804e22730475bea7e))
- **HTML run reports**: generates a self-contained HTML report on shutdown with
  run summary, per-agent performance stats, configuration details, dark theme,
  and color-coded tables. Saved as
  `agent_farm_report_YYYYMMDD_HHMMSS.html`.
  ([`b4f211d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b4f211d4269ef8c0c942511804e22730475bea7e))
- **Shell completion**: new `install-completion` CLI command with auto-detection
  for bash, zsh, and fish.
  ([`b4f211d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b4f211d4269ef8c0c942511804e22730475bea7e))

### Agent improvements (4 key improvements)

- **Dynamic chunk sizing**: `chunk_size` is now configurable in JSON configs,
  allowing larger or smaller problem slices per agent.
- **Tmux pane title context warnings**: pane titles are updated to show context
  percentage so operators can spot pressure at a glance.
- **Heartbeat tracking system**: each agent writes a heartbeat file on every
  tmux send and when actively working; agents with heartbeats older than 120s
  are flagged as stuck. Status table shows heartbeat age with color coding.
  Files are cleaned up on shutdown.
- **Pre-flight verifier** (`claude-code-agent-farm doctor`): comprehensive system
  check covering Python version, tmux, `cc` alias, Claude installation, API
  config, git, uv, file permissions, and project-specific tool detection.
  Returns proper exit codes for CI/CD integration.
  ([`89a7730`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/89a77309d1266d6482095c84c5242419cb89e2c0),
  [`443f055`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/443f05596d1c55c84218030427095252cfa98bab))

### Agent improvements (5 key improvements)

- **Context-reset macro** (Ctrl+R): broadcasts `/reset` (later changed to
  `/clear`) to all agent panes with a single keystroke from the controller
  window.
- **Incremental commit option** (`--commit-every N`): commits after every N
  regeneration cycles across all agents, preventing giant single diffs.
- **Rich diff reporter**: after each commit, displays a formatted panel with
  file-level change counts (modified/added/deleted) using Rich.
- **Adaptive stagger**: halves launch delay on success, doubles on failure
  (capped at 60s), for faster healthy startups.
- Setup script improvements: alias auto-detection and patching of common
  mis-quotings.
  ([`751a8c4`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/751a8c4bb4f468864114392b9eb257d02dd3a5b2))

### README updates

- Integrated all new features into a cohesive README rather than documenting
  them as additions.
  ([`a73d0ca`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/a73d0ca7e9f8ca9d4cb1956e2331a31e3103109b),
  [`c9cca66`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/c9cca665e283b39f68396857c6d22722439f2238))

### Cooperating agents workflow

- **New coordinating/cooperating agents prompt**: implements a distributed
  lock-based coordination protocol where agents claim files via lock files,
  register work plans in a shared registry, check for conflicts before starting,
  and log completed work. Enables 20+ agents to perform strategic, non-trivial
  improvements (refactoring, architecture changes, security hardening) on the
  same codebase without merge conflicts.
  ([`a1c6073`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/a1c607396ba7745e8dc5aa7cd36c2297f06a64f1))
- **PostgreSQL 17 & Python Best Practices** guide (2,700+ lines) for
  FastAPI/SQLModel stacks.
  ([`a1c6073`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/a1c607396ba7745e8dc5aa7cd36c2297f06a64f1))

---

## 2025-06-29 — 2025-06-30 — Multi-stack expansion (34 technology stacks)

This is the largest expansion phase. The project was generalized from a
Next.js-only tool to a multi-stack, multi-workflow orchestration framework.

### Best practices guides added (17 new guides)

New comprehensive guides covering thousands of lines each:

- Go Web Apps, Java Enterprise, Python FastAPI, SvelteKit 2,
  Remix/Astro, Rust System Programming, Rust Web Apps
  ([`97d8803`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/97d88031cbfd70e430e59e75a6488c949fdacce3))
- Angular, Ansible DevOps, Cosmos/Golang Blockchain, C++ Systems Programming,
  Data Lakes (Kafka/Snowflake/Spark), Excel Automation (Python/Azure),
  Flutter, Hardware Development, HashiCorp Vault Policy-as-Code,
  Laravel, PHP, Polars/DuckDB Data Engineering, Rust CLI Tools,
  Security Engineering, Solana/Anchor, Unreal Engine 5, React Native
  ([`2ac4167`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/2ac416740016fc1545cb42263f87e597cf6ba1ef),
  [`e55816d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/e55816d1daf7f5159c1eccfe52023952e4bd9108))

### Config files and prompts

- Stack-specific JSON configs and best-practices prompts for all 34 stacks
  including SvelteKit, Terraform/Azure, Go, Java, Rust (system, web, CLI),
  Bash/Zsh, cloud-native DevOps, GenAI/LLM ops, data engineering, serverless
  edge, Angular, Flutter, PHP/Laravel, Solana, Ansible, Kubernetes AI, LLM
  dev/testing, LLM eval/observability, React Native, Polars/DuckDB, Vault,
  security engineering, Unreal Engine, Cosmos, data lakes, Excel automation,
  hardware dev, and C++ systems.
  ([`4babf48`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/4babf4830393cde7837eac5631639c5ba9310982),
  [`9f0a7dc`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/9f0a7dcd08d8e8d32c58b061b5ddcbcf322dbc93),
  [`e55816d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/e55816d1daf7f5159c1eccfe52023952e4bd9108),
  [`3899d2d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/3899d2d114fec6d36b79d514a4d2e0f1fd8d3030))

### Tool setup scripts (24 scripts)

Interactive, shell-agnostic installation scripts with smart detection of
existing tools and non-destructive operation:

**Phase 1** (10 scripts):
Python FastAPI, Go Web Apps, Next.js, SvelteKit/Remix/Astro, Rust, Java
Enterprise, Bash/Zsh, Cloud Native DevOps, GenAI/LLM Ops, Data Engineering,
Serverless Edge.
([`4babf48`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/4babf4830393cde7837eac5631639c5ba9310982))

**Phase 2** (8 scripts):
Angular, Flutter, PHP/Laravel, Solana/Anchor, Ansible, React Native,
Terraform/Azure, Excel Automation, Rust CLI, HashiCorp Vault, Polars/DuckDB.
([`9f0a7dc`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/9f0a7dcd08d8e8d32c58b061b5ddcbcf322dbc93),
[`2211f28`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/2211f28b784f6334a3f2b2ce672ccfb7a3080031),
[`3899d2d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/3899d2d114fec6d36b79d514a4d2e0f1fd8d3030),
[`acca24a`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/acca24adf16c6916e5f74946160c31213bcbd077))

**Phase 3** (5 scripts):
Unreal Engine, Cosmos Blockchain, Data Lakes, Hardware Dev, Security Engineering.
([`67e8299`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/67e8299c5cce6c152c20fa52f35d85d905e6f1d2))

Common utilities library (`tool_setup_scripts/common_utils.sh`) and interactive
menu script (`tool_setup_scripts/setup.sh`) added for shared helpers across all
setup scripts.

### Modularization and best-practices workflow

- **Modular problem-command system**: removed hardcoded default prompt; problem
  commands are now configurable per tech stack. Python (mypy/ruff) and Next.js
  (bun/eslint/tsc) supported out of the box.
  ([`cb34635`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/cb3463501f481a3b1f5a883b99736adeab26a279))
- **`best_practices_files` config option**: replaced `best_practices_dir` with
  file-level selection for precise control over which guides to include.
  ([`846cf12`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/846cf124e3dca164c5caa58f1b65aa7e49f00732))
- **Best practices implementation workflow**: new prompt type with variable
  substitution; agents read a guide, create a progress-tracking document, and
  implement improvements in configurable `chunk_size` batches. Includes a
  "continue" prompt for resuming existing work across sessions.
  ([`fcba99c`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/fcba99cbc69157ac3334418fc7886a276b4de7a9))
- **UI polish**: Rich box styles (DOUBLE for banner, ROUNDED for tables) and
  `textwrap` for long paths, prompt previews, and error messages.
  ([`821f929`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/821f92924bb3bb7edc42b9f98d49b43d43f13fbc))
- Comprehensive README rewrite removing Next.js-specific focus and presenting
  the project as a general framework.
  ([`f7a350e`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/f7a350edf8603e7c3db1fac95187486302600b8b),
  [`97d8803`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/97d88031cbfd70e430e59e75a6488c949fdacce3))

---

## 2025-06-28 — Initial release and stabilization

### Added (initial commit)

- **Core orchestrator** (`claude_code_agent_farm.py`): launches and manages
  multiple Claude Code (`cc`) sessions in parallel via tmux, with a monitoring
  dashboard, automatic problem-file generation, agent health checks, and
  graceful shutdown.
- **`view_agents.sh`**: optional convenience script for viewing the tmux session
  in grid, focus, or split modes.
- **Setup script** (`setup.sh`): installs prerequisites, creates a Python 3.13
  venv, configures the `cc` alias, and sets up direnv.
- Sample JSON configuration and Next.js bug-fixing prompt.
- `pyproject.toml` with CLI entry point `claude-code-agent-farm`.
  ([`7137755`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/7137755cd85989baf95feca9179bb97040c475af))

### Stabilization (same day, 7 commits)

Rapid-fire fixes bringing the orchestrator from proof-of-concept to production
quality over approximately 5 hours:

- **Settings backup/restore system**: `_backup_claude_settings()`,
  `_restore_claude_settings()` with timestamped tarballs to prevent corruption
  from concurrent agents.
  ([`6ddc893`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/6ddc8932be93b957d47dcfd8a445c5a95d28a5ef))
- **File locking**: `_acquire_claude_lock()` / `_release_claude_lock()` for
  concurrent access safety.
  ([`6ddc893`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/6ddc8932be93b957d47dcfd8a445c5a95d28a5ef))
- **Shell-prompt wait** (`_wait_for_shell_prompt()`): waits for a proper shell
  prompt before sending commands to a pane, preventing race conditions.
  ([`97869b7`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/97869b7d23b4d9257b59a679da6c2178c80655d3))
- **Claude permissions check** (`_check_claude_permissions()`): verifies Claude
  Code is configured with required permissions before launch.
  ([`34c7731`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/34c773112fcf74d686050b4b449745f6e9299291))
- **Interruptible confirmation** (`interruptible_confirm()`): Ctrl+C during
  prompts triggers graceful shutdown instead of a traceback.
  ([`97869b7`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/97869b7d23b4d9257b59a679da6c2178c80655d3))
- **Welcome-screen detection**: `has_welcome_screen()` identifies Claude Code's
  welcome output so agents are not prematurely considered idle.
  ([`6ddc893`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/6ddc8932be93b957d47dcfd8a445c5a95d28a5ef))
- Binary-safe `tmux_send()` with retry logic (3 retries, exponential backoff).
- Expanded `view_agents.sh` with additional viewing modes.
- Setup script hardened with better prerequisite checking and error handling.
  ([`57f5c75`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/57f5c75a23c95b061fca77d96ffeaab1c191bf19),
  [`ab29709`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/ab29709c3abf918f791ddacd5e0308c596fa5c80),
  [`f905a1f`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/f905a1f4ebb50619d2133e541ae21c7a1e3171eb),
  [`34c7731`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/34c773112fcf74d686050b4b449745f6e9299291),
  [`4a2103c`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/4a2103cbfec618e886ab713488f33fe726f55d29))
