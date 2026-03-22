# Changelog

All notable changes to Claude Code Agent Farm are documented in this file.

This project has no tagged releases or GitHub Releases. Changes are organized
chronologically by date, grouped into development phases, and within each phase
organized by capability area rather than raw commit order. Every entry links to
its commit on GitHub.

Repository: <https://github.com/Dicklesworthstone/claude_code_agent_farm>

---

## 2026-02-21 / 2026-02-22 -- License and branding

### Licensing

- Replaced plain MIT license with **MIT + OpenAI/Anthropic Rider**, restricting
  use by OpenAI, Anthropic, and their affiliates without express written
  permission from Jeffrey Emanuel.
  ([`66647df`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/66647df11ba94102ab88c9a03afdc41f87db6f11))
- Updated all README badges and references to reflect the new license.
  ([`f6c0bb3`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/f6c0bb358b70a5d90059d6eb32f24258aad783cc))

### Social / branding

- Added GitHub social preview image (1280x640) for consistent link previews.
  ([`dee3271`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/dee32719b58a78fb47b3b33bb0fa00e7775f08c3))

---

## 2025-09-25 -- Next.js best-practices update

### Best practices content

- Extended the Next.js 15 best practices guide with a new section on React
  `useEffect` guidelines for Next.js 15 alongside TanStack Query and Zustand,
  covering when to avoid effects, proper cleanup patterns, and server-first
  alternatives.
- Updated the API generation script URL in the guide.
  ([`ed68548`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/ed6854825e413459f20a2eabc27342150959448b))

---

## 2025-07-19 -- FastMCP best practices guide

### Best practices content

- Added new **Python FastMCP Best Practices** guide
  (`best_practices_guides/PYTHON_FASTMCP_BEST_PRACTICES.md`, 900+ lines).
  ([`1e50891`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/1e508915bab610ac37bf2edf694672cdb1b9b03b))

---

## 2025-07-06 -- Smarter recovery and context management

### Agent health and recovery

- `needs_restart()` now returns a reason string (`"context"`, `"error"`,
  `"idle"`) instead of a boolean, enabling differentiated recovery strategies:
  agents with low context receive `/clear` instead of a full restart, avoiding
  settings-file races.
- New `clear_agent_context()` method sends `/clear` and re-injects the working
  prompt without restarting Claude Code.
- Active shell-prompt probe: after 3 seconds of passive detection, the system
  sends an `echo` command with a unique random marker to positively confirm
  shell readiness, accommodating minimal or custom shell prompts.
  ([`6d731f3`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/6d731f31d5642e1c21ffe2c898fa8fb7acf409a8))

### Configuration defaults

- Default agent count reduced from 20 to 6 for safer out-of-the-box behavior.
- Context-reset macro changed from `/reset` to `/clear` (Ctrl+R broadcast).
  ([`6d731f3`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/6d731f31d5642e1c21ffe2c898fa8fb7acf409a8))

### Best practices content

- DSPy and Python LLM Pipeline best practices guide condensed and restructured.
  ([`6d731f3`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/6d731f31d5642e1c21ffe2c898fa8fb7acf409a8))

---

## 2025-07-02 / 2025-07-03 -- Huge prompt support, .gitignore management, and new guides

### Prompt delivery

- **Huge prompt support**: `tmux_send()` rewritten to use the tmux buffer API
  (`load-buffer` / `paste-buffer`) with a temporary file, making arbitrarily
  large prompts safe regardless of shell-quoting limits.
  ([`fdcfa48`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/fdcfa4865a6951e7cead2e6c313cccf66e87f177))

### Project hygiene

- **Automatic `.gitignore` management**: new `_ensure_gitignore_entries()`
  idempotently adds patterns for `.heartbeats/`, state files, backup
  directories, and HTML reports to the target project's `.gitignore` (creates
  the file if missing).
  ([`1bd15bd`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/1bd15bd536f87329266e9feaa8157088d3aa78cc))

### Best practices content

- Added **DSPy and Python LLM Pipeline Best Practices** guide (3,400+ lines).
  ([`b3f0223`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b3f0223be4c7363fd6dc6bda3e45726845e8f1eb))
- Expanded **PostgreSQL 17 & Python** best practices guide with significantly
  more content.
  ([`a92a0bb`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/a92a0bbcd023dcc6227209f11608472c8036a71f))

---

## 2025-07-01 / 2025-07-02 -- Cooperating agents, major monitoring upgrades, and reporting

This phase introduced the most sophisticated workflow (coordinating agents) and
nine major orchestration improvements across two batches.

### Cooperating agents workflow

- **Distributed lock-based coordination protocol**: a new prompt file implements
  a multi-agent coordination system where agents generate unique IDs, claim
  files via lock files, register work plans in a shared
  `coordination/active_work_registry.json`, check for conflicts before starting,
  handle stale locks (>2 hours), and log completed work. Enables 20+ agents to
  perform strategic, non-trivial improvements (refactoring, architecture
  changes, security hardening) on the same codebase without merge conflicts.
  All coordination is achieved purely through the prompt -- no code changes
  required.
  ([`a1c6073`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/a1c607396ba7745e8dc5aa7cd36c2297f06a64f1))
- Added **PostgreSQL 17 & Python Best Practices** guide (2,700+ lines) for
  FastAPI/SQLModel stacks, alongside a cooperating-agents config.
  ([`a1c6073`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/a1c607396ba7745e8dc5aa7cd36c2297f06a64f1))

### Monitoring and observability

- **Heartbeat tracking system**: each agent writes a heartbeat file on every
  tmux command send and when actively working; agents with heartbeats older than
  120 seconds are flagged as stuck. Status table shows heartbeat age with color
  coding. Files are cleaned up on shutdown.
  ([`89a7730`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/89a77309d1266d6482095c84c5242419cb89e2c0))
- **Context-window early-warning in tmux pane titles**: pane titles show agent
  status and context percentage with warning indicators when context drops
  below threshold.
  ([`89a7730`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/89a77309d1266d6482095c84c5242419cb89e2c0))
- **Adaptive idle timeout**: tracks cycle-completion times across all agents and
  sets timeout to 3x the median (bounded 30s -- 600s), preventing false
  positives on complex tasks while speeding detection on simple ones.
  ([`b4f211d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b4f211d4269ef8c0c942511804e22730475bea7e))
- **HTML run reports**: generates a self-contained HTML report on shutdown with
  run summary, per-agent performance stats, configuration details, dark theme,
  and color-coded tables. Saved as `agent_farm_report_YYYYMMDD_HHMMSS.html`.
  ([`b4f211d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b4f211d4269ef8c0c942511804e22730475bea7e))
- **Rich diff reporter**: after each commit, displays a formatted panel with
  file-level change counts (modified/added/deleted) using Rich.
  ([`751a8c4`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/751a8c4bb4f468864114392b9eb257d02dd3a5b2))

### Agent lifecycle and control

- **Dynamic chunk sizing**: `_calculate_dynamic_chunk_size()` computes optimal
  chunk size based on remaining work (`max(10, total_lines / agents / 2)`),
  updating prompt text dynamically.
  ([`89a7730`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/89a77309d1266d6482095c84c5242419cb89e2c0))
- **Pre-flight verifier** (`claude-code-agent-farm doctor`): comprehensive
  system check covering Python version, tmux, `cc` alias, Claude installation,
  API config, git, uv, file permissions, and project-specific tool detection.
  Returns proper exit codes for CI/CD.
  ([`89a7730`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/89a77309d1266d6482095c84c5242419cb89e2c0),
  [`443f055`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/443f05596d1c55c84218030427095252cfa98bab))
- **Context-reset macro** (Ctrl+R): broadcasts `/reset` to all agent panes
  from the controller window with a single keystroke.
  ([`751a8c4`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/751a8c4bb4f468864114392b9eb257d02dd3a5b2))
- **Incremental commit option** (`--commit-every N`): commits after every N
  regeneration cycles across all agents, preventing giant single diffs.
  ([`751a8c4`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/751a8c4bb4f468864114392b9eb257d02dd3a5b2))
- **Adaptive stagger**: halves launch delay on success, doubles on failure
  (capped at 60s), for faster healthy startups.
  ([`751a8c4`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/751a8c4bb4f468864114392b9eb257d02dd3a5b2))
- **Double Ctrl+C force-kill**: first Ctrl+C triggers graceful shutdown; a
  second within 3 seconds force-kills the tmux session and exits immediately.
  ([`b4f211d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b4f211d4269ef8c0c942511804e22730475bea7e))

### Backup and safety

- **Size-based backup rotation**: `_cleanup_old_backups()` now enforces a 200 MB
  total-size limit in addition to a count limit, preventing disk bloat.
  ([`b4f211d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b4f211d4269ef8c0c942511804e22730475bea7e))

### CLI and developer experience

- **Shell completion**: new `install-completion` CLI command with auto-detection
  for bash, zsh, and fish.
  ([`b4f211d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/b4f211d4269ef8c0c942511804e22730475bea7e))
- Setup script enhanced with automatic detection and patching of common
  `cc` alias mis-quotings.
  ([`751a8c4`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/751a8c4bb4f468864114392b9eb257d02dd3a5b2))

### Documentation

- README integrated all new features into a cohesive whole rather than
  documenting them as additions.
  ([`a73d0ca`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/a73d0ca7e9f8ca9d4cb1956e2331a31e3103109b),
  [`c9cca66`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/c9cca665e283b39f68396857c6d22722439f2238))

---

## 2025-06-29 / 2025-06-30 -- Multi-stack expansion (34 technology stacks)

The largest expansion phase. The project was generalized from a Next.js-only
bug-fixing tool into a multi-stack, multi-workflow orchestration framework
supporting 34 technology stacks.

### Orchestrator architecture

- **Modular problem-command system**: removed hardcoded default prompt;
  `problem_commands` are now fully configurable per tech stack in JSON configs.
  Python (mypy/ruff) and Next.js (bun/eslint/tsc) supported out of the box.
  ([`cb34635`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/cb3463501f481a3b1f5a883b99736adeab26a279))
- **`best_practices_files` config option**: replaced `best_practices_dir` with
  file-level selection for precise control over which guides to include.
  ([`846cf12`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/846cf124e3dca164c5caa58f1b65aa7e49f00732))
- **Best practices implementation workflow**: new prompt type with variable
  substitution; agents read a guide, create a progress-tracking document, and
  implement improvements in configurable `chunk_size` batches. Includes a
  "continue" prompt for resuming existing work across sessions.
  ([`fcba99c`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/fcba99cbc69157ac3334418fc7886a276b4de7a9))

### UI polish

- Rich box styles (DOUBLE for banner, ROUNDED for tables) and `textwrap` for
  long paths, prompt previews, and error messages.
  ([`821f929`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/821f92924bb3bb7edc42b9f98d49b43d43f13fbc))

### Best practices guides (17 new guides)

Comprehensive, multi-thousand-line guides covering:

**Web and mobile frameworks:**
SvelteKit 2, Remix/Astro, Angular, Flutter, Laravel, PHP, React Native

**Systems languages:**
Go Web Apps, Java Enterprise, Python FastAPI, Rust System Programming,
Rust Web Apps, Rust CLI Tools, C++ Systems Programming

**DevOps, infrastructure, and security:**
HashiCorp Vault Policy-as-Code, Security Engineering

**Data and AI:**
Data Lakes (Kafka/Snowflake/Spark), Excel Automation (Python/Azure),
Polars/DuckDB Data Engineering

**Blockchain and specialized:**
Cosmos/Golang Blockchain, Solana/Anchor, Unreal Engine 5,
Hardware Development

([`97d8803`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/97d88031cbfd70e430e59e75a6488c949fdacce3),
[`2ac4167`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/2ac416740016fc1545cb42263f87e597cf6ba1ef),
[`e55816d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/e55816d1daf7f5159c1eccfe52023952e4bd9108))

### Config files and prompts

- Stack-specific JSON configs and best-practices prompts for all 34 stacks.
  ([`4babf48`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/4babf4830393cde7837eac5631639c5ba9310982),
  [`9f0a7dc`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/9f0a7dcd08d8e8d32c58b061b5ddcbcf322dbc93),
  [`e55816d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/e55816d1daf7f5159c1eccfe52023952e4bd9108),
  [`3899d2d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/3899d2d114fec6d36b79d514a4d2e0f1fd8d3030))

### Tool setup scripts (24 scripts)

Interactive, shell-agnostic installation scripts with smart detection of
existing tools and non-destructive operation. Common utilities library
(`tool_setup_scripts/common_utils.sh`) and interactive menu
(`tool_setup_scripts/setup.sh`) provide shared helpers.

**Phase 1** -- core stacks (10 scripts):
Python FastAPI, Go Web Apps, Next.js, SvelteKit/Remix/Astro, Rust,
Java Enterprise, Bash/Zsh, Cloud Native DevOps, GenAI/LLM Ops,
Data Engineering, Serverless Edge.
([`4babf48`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/4babf4830393cde7837eac5631639c5ba9310982),
[`3854c67`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/3854c67dd1977c1361c075c98a20442248965ad4))

**Phase 2** -- expanded coverage (8+ scripts):
Angular, Flutter, PHP/Laravel, Solana/Anchor, Ansible, React Native,
Terraform/Azure, C++ Systems, Excel Automation, Rust CLI, HashiCorp Vault,
Polars/DuckDB, Kubernetes AI Inference, LLM Dev Testing,
LLM Eval/Observability.
([`9f0a7dc`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/9f0a7dcd08d8e8d32c58b061b5ddcbcf322dbc93),
[`2211f28`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/2211f28b784f6334a3f2b2ce672ccfb7a3080031),
[`3899d2d`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/3899d2d114fec6d36b79d514a4d2e0f1fd8d3030),
[`acca24a`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/acca24adf16c6916e5f74946160c31213bcbd077))

**Phase 3** -- remaining stacks (5 scripts):
Unreal Engine, Cosmos Blockchain, Data Lakes, Hardware Dev,
Security Engineering.
([`67e8299`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/67e8299c5cce6c152c20fa52f35d85d905e6f1d2))

### Documentation

- Comprehensive README rewrite removing Next.js-specific focus and presenting
  the project as a general multi-stack framework.
  ([`f7a350e`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/f7a350edf8603e7c3db1fac95187486302600b8b),
  [`97d8803`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/97d88031cbfd70e430e59e75a6488c949fdacce3))
- Cleanup: restored `view_agents.sh`, removed duplicate prompt files.
  ([`2dd3b7c`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/2dd3b7ccea3ea05c0ec6a4e3deef4ae166a24e9a))

---

## 2025-06-28 -- Initial release and day-one stabilization

The project was created and brought from proof-of-concept to production quality
in a single day through the initial commit and seven rapid-fire stabilization
commits over approximately five hours.

### Core orchestrator

- **`claude_code_agent_farm.py`**: launches and manages multiple Claude Code
  (`cc`) sessions in parallel via tmux, with a Rich monitoring dashboard,
  automatic problem-file generation from configured type-check and lint
  commands, agent health checks, and graceful Ctrl+C shutdown.
- **`view_agents.sh`**: optional convenience script for viewing the tmux session
  in grid, focus, or split modes.
- **`setup.sh`**: installs prerequisites, creates a Python 3.13 venv via `uv`,
  configures the `cc` alias, and sets up direnv.
- Sample JSON configuration and Next.js bug-fixing prompt.
- `pyproject.toml` with CLI entry point `claude-code-agent-farm`.
  ([`7137755`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/7137755cd85989baf95feca9179bb97040c475af))

### Concurrency and safety (stabilization)

- **Settings backup/restore system**: `_backup_claude_settings()` /
  `_restore_claude_settings()` with timestamped compressed tarballs to prevent
  `~/.claude` corruption when many agents start concurrently. Essential backup
  only (excludes large caches) with selective size-based filtering.
  ([`6ddc893`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/6ddc8932be93b957d47dcfd8a445c5a95d28a5ef),
  [`34c7731`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/34c773112fcf74d686050b4b449745f6e9299291))
- **File locking**: `_acquire_claude_lock()` / `_release_claude_lock()` for
  concurrent access safety around shared resources.
  ([`6ddc893`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/6ddc8932be93b957d47dcfd8a445c5a95d28a5ef))
- Increased stagger delay from 4s to 10s and post-launch wait from 3s to 15s
  to prevent settings clobbering between concurrent agent starts.
  ([`34c7731`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/34c773112fcf74d686050b4b449745f6e9299291))

### Agent state detection (stabilization)

- **Shell-prompt wait** (`_wait_for_shell_prompt()`): waits for a proper shell
  prompt before sending commands to a pane, preventing race conditions.
  ([`97869b7`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/97869b7d23b4d9257b59a679da6c2178c80655d3))
- **Expanded ready-state detection** (`is_claude_ready()`): now checks multiple
  indicators (welcome message, prompt box patterns, help text, bypassing
  permissions indicator) instead of a single string match.
  ([`34c7731`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/34c773112fcf74d686050b4b449745f6e9299291))
- **Welcome-screen detection** (`has_welcome_screen()`): identifies Claude
  Code's setup/onboarding screens so agents are not prematurely considered idle.
  ([`6ddc893`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/6ddc8932be93b957d47dcfd8a445c5a95d28a5ef))
- **Expanded error detection**: additional indicators for login prompts, auth
  failures, configuration corruption, and Claude-specific error messages.
  False-positive guard: `has_settings_error()` now returns `False` if the agent
  is actually in a ready state.
  ([`97869b7`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/97869b7d23b4d9257b59a679da6c2178c80655d3),
  [`34c7731`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/34c773112fcf74d686050b4b449745f6e9299291))

### Robustness (stabilization)

- **Binary-safe `tmux_send()`**: uses tmux literal mode (`-l`) with
  `shlex.quote()` and retry logic (3 retries, exponential backoff) instead of
  fragile shell-quoting.
  ([`57f5c75`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/57f5c75a23c95b061fca77d96ffeaab1c191bf19))
- **Interruptible confirmation** (`interruptible_confirm()`): Ctrl+C during
  prompts triggers graceful shutdown instead of a traceback.
  ([`97869b7`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/97869b7d23b4d9257b59a679da6c2178c80655d3))
- **Claude permissions check** (`_check_claude_permissions()`): verifies Claude
  Code is configured with required permissions before launch.
  ([`34c7731`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/34c773112fcf74d686050b4b449745f6e9299291))
- Encoding-safe `line_count()` with UTF-8/latin-1 fallback.
- `run()` helper improved: capture mode returns properly typed output; quiet
  mode preserves stderr for exception detail.
- Expanded `view_agents.sh` with additional viewing modes.
- Setup script hardened with better prerequisite checking and error handling.
  ([`57f5c75`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/57f5c75a23c95b061fca77d96ffeaab1c191bf19),
  [`ab29709`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/ab29709c3abf918f791ddacd5e0308c596fa5c80),
  [`f905a1f`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/f905a1f4ebb50619d2133e541ae21c7a1e3171eb),
  [`34c7731`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/34c773112fcf74d686050b4b449745f6e9299291),
  [`4a2103c`](https://github.com/Dicklesworthstone/claude_code_agent_farm/commit/4a2103cbfec618e886ab713488f33fe726f55d29))
