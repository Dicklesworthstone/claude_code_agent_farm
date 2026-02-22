# Claude Code Agent Farm 🤖🚜

> Orchestrate multiple Claude Code agents working in parallel to improve your codebase through automated bug fixing or systematic best practices implementation

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT%2BOpenAI%2FAnthropic%20Rider-blue.svg)](./LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## 🎯 What is this?

Claude Code Agent Farm is a powerful orchestration framework that runs multiple Claude Code (`cc`) sessions in parallel to systematically improve your codebase. It supports multiple technology stacks and workflow types, allowing teams of AI agents to work together on large-scale code improvements.

### Key Features

- 🚀 **Parallel Processing**: Run 20+ Claude Code agents simultaneously (up to 50 with `max_agents` config)
- 🎯 **Multiple Workflows**: Bug fixing, best practices implementation, or coordinated multi-agent development
- 🤝 **Agent Coordination**: Advanced lock-based system prevents conflicts between parallel agents
- 🌐 **Multi-Stack Support**: 34 technology stacks including Next.js, Python, Rust, Go, Java, Angular, Flutter, C++, and more
- 📊 **Smart Monitoring**: Real-time dashboard with context warnings, heartbeat tracking, and tmux pane titles
- 🔄 **Auto-Recovery**: Automatically restarts agents when needed with adaptive idle timeout based on work patterns
- 📈 **Progress Tracking**: Git commits with rich diff summaries and comprehensive HTML run reports
- 🔄 **Context Management**: Agents automatically clear their own context when nearing limits, plus one-key broadcast of /clear to all agents (Ctrl+R)
- ⚙️ **Highly Configurable**: JSON configs with variable substitution and dynamic chunk sizing
- 🖥️ **Flexible Viewing**: Multiple tmux viewing modes with shell completion support
- 🔒 **Safe Operation**: Automatic settings backup/restore with size-based rotation, file locking, atomic operations
- 🛠️ **Development Setup**: 24 integrated tool installation scripts and pre-flight verification
- 🎯 **Smart Controls**: Graceful shutdown with force-kill on double Ctrl+C within 3 seconds

## 📋 Prerequisites

- **Python 3.13+** (managed by `uv`)
- **tmux** (for terminal multiplexing)
- **Claude Code** (`claude` command installed and configured)
- **git** (for version control)
- **Your project's tools** (e.g., `bun` for Next.js, `mypy`/`ruff` for Python)
- **direnv** (optional but recommended for automatic environment activation)
- **uv** (modern Python package manager)

### Important: The `cc` Alias

The agent farm requires a special `cc` alias to launch Claude Code with the necessary permissions:

```bash
alias cc="ENABLE_BACKGROUND_TASKS=1 claude --dangerously-skip-permissions"
```

This alias will be configured automatically by the setup script.

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/Dicklesworthstone/claude_code_agent_farm.git
cd claude_code_agent_farm
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Check and install missing prerequisites
- Create a Python 3.13 virtual environment
- Install all dependencies
- Configure the `cc` alias with automatic detection and fixing of common mis-quotings
- Validate existing aliases and patch incorrect quote patterns
- Set up direnv for automatic environment activation
- Handle both bash and zsh shells automatically

### 2. Verify Your Setup

Run the pre-flight verifier to ensure everything is configured correctly:

```bash
claude-code-agent-farm doctor --path /path/to/project
```

This command checks:
- Python version compatibility
- Required tools installation (tmux, git, uv)
- Claude Code configuration and API keys
- Project-specific tool availability
- File permissions and common issues

### 3. Enable Shell Completion (Optional)

For faster command entry with tab completion:

```bash
# Auto-detect shell and install completion
claude-code-agent-farm install-completion

# Or specify shell explicitly
claude-code-agent-farm install-completion --shell bash
claude-code-agent-farm install-completion --shell zsh
claude-code-agent-farm install-completion --shell fish
```

### 4. Choose Your Workflow

#### For Bug Fixing (Traditional)
```bash
# Next.js project
claude-code-agent-farm --path /path/to/project --config configs/nextjs_config.json

# Python project
claude-code-agent-farm --path /path/to/project --config configs/python_config.json
```

#### For Best Practices Implementation
```bash
# Ensure you have a best practices guide in place
cp best_practices_guides/NEXTJS15_BEST_PRACTICES.md /path/to/project/best_practices_guides/

# Run with best practices config
claude-code-agent-farm --path /path/to/project --config configs/nextjs_best_practices_config.json
```

## 🛠️ Tool Setup Scripts

The project includes a comprehensive modular system for setting up development environments:

### Available Setup Scripts

Run the interactive menu:
```bash
cd tool_setup_scripts
./setup.sh
```

Or run specific setups directly:

1. **Python FastAPI** (`setup_python_fastapi.sh`)
   - Python 3.12+, uv, ruff, mypy, pre-commit, ipython

2. **Go Web Apps** (`setup_go_webapps.sh`)
   - Go 1.23+, golangci-lint, air, migrate, mockery, Task, swag

3. **Next.js** (`setup_nextjs.sh`)
   - Node.js 22+, Bun, pnpm, TypeScript, ESLint, Prettier

4. **SvelteKit/Remix/Astro** (`setup_sveltekit_remix_astro.sh`)
   - Extends Next.js setup with Vite, Playwright, Vitest, Biome

5. **Rust Development** (`setup_rust.sh`)
   - Rust toolchain, cargo tools, web & system programming tools

6. **Java Enterprise** (`setup_java_enterprise.sh`)
   - Java 21 LTS, SDKMAN, Gradle 8.11+, Maven 3.9+, JBang

7. **Bash/Zsh Scripting** (`setup_bash_zsh.sh`)
   - Shell development tools and best practices

8. **Cloud Native DevOps** (`setup_cloud_native_devops.sh`)
   - Docker, Kubernetes, Terraform, cloud tools

9. **GenAI/LLM Ops** (`setup_genai_llm_ops.sh`)
   - ML/AI development tools and frameworks

10. **Data Engineering** (`setup_data_engineering.sh`)
    - Data processing and analytics tools

11. **Serverless Edge** (`setup_serverless_edge.sh`)
    - Serverless and edge computing tools

12. **Terraform Azure** (`setup_terraform_azure.sh`)
    - Terraform, Azure CLI, infrastructure tools

13. **Angular** (`setup_angular.sh`)
    - Node.js, Angular CLI, TypeScript, testing tools

14. **Flutter** (`setup_flutter.sh`)
    - Flutter SDK, Dart, Android Studio, development tools

15. **React Native** (`setup_react_native.sh`)
    - React Native CLI, mobile development tools

Additional setup scripts are available for:
- **PHP/Laravel** (`setup_php_laravel.sh`)
- **C++ Systems** (`setup_cpp_systems.sh`)
- **Solana/Anchor** (`setup_solana_anchor.sh`)
- **Ansible** (`setup_ansible.sh`)
- **LLM Dev Testing** (`setup_llm_dev_testing.sh`)
- **LLM Eval Observability** (`setup_llm_eval_observability.sh`)
- **Kubernetes AI** (`setup_kubernetes_ai_inference.sh`)

### Setup Features

- 🎨 **Interactive & Safe**: Colorful prompts, always asks before installing
- 🔍 **Smart Detection**: Checks existing installations to avoid conflicts
- 🛡️ **Non-Destructive**: Won't overwrite configurations without permission
- 🐚 **Shell Agnostic**: Works with both bash and zsh
- 📊 **Progress Tracking**: Shows what's installed and what's pending

## 📖 Understanding the Architecture

### The Two-Script System

This project consists of two independent scripts that work together:

#### 1. **Python Script** (`claude_code_agent_farm.py`) - The Brain 🧠

This is the main orchestrator that does all the heavy lifting:

- **Creates and manages tmux sessions** with multiple panes
- **Generates the problems file** by running configured commands
- **Launches Claude Code agents** in each tmux pane
- **Monitors agent health** (context usage, work status, errors)
- **Auto-restarts agents** when they complete tasks or hit issues
- **Runs monitoring dashboard** in the tmux controller window
- **Handles graceful shutdown** with Ctrl+C
- **Manages settings backup/restore** to prevent corruption
- **Implements file locking** for concurrent access safety
- **Writes monitor state** to JSON file for external monitoring

**You run this script and it stays running** (unless using `--no-monitor` mode). The monitoring dashboard is displayed in the tmux session's controller window, not in the launching terminal.

#### 2. **Shell Script** (`view_agents.sh`) - The Window 🪟

This is an optional convenience tool for viewing the tmux session:

- **It does NOT interact with the Python script**
- **Run it in a separate terminal** to peek at agent activity
- **Provides different viewing modes** (grid, focus, split)
- **Just a wrapper around tmux commands** for convenience
- **Automatically suggests font size adjustments** for many agents

Think of it like this:
- **Python script** = Your car engine (does all the work)
- **Shell script** = Your dashboard camera (lets you see what's happening)

### Hidden Commands

#### Monitor-Only Mode
There's a hidden command for running just the monitor display:

```bash
claude-code-agent-farm monitor-only --path /project --session claude_agents
```

This reads the monitor state file and displays the dashboard without launching agents.

### Why Two Scripts?

1. **Separation of Concerns**: Core logic (Python) vs viewing utilities (shell)
2. **Flexibility**: You can monitor agents without the viewer script
3. **Independence**: Either script can be used without the other

## 🎮 Supported Workflows

### 1. Bug Fixing Workflow

Agents work through type-checker and linter problems in parallel:
- Runs your configured type-check and lint commands
- Generates a combined problems file
- Agents select random chunks to fix
- Marks completed problems to avoid duplication
- Focuses on fixing existing issues
- Uses instance-specific seeds for better randomization

### 2. Best Practices Implementation Workflow

Agents systematically implement modern best practices:
- Reads a comprehensive best practices guide
- Creates a progress tracking document (`@<STACK>_BEST_PRACTICES_IMPLEMENTATION_PROGRESS.md`)
- Implements improvements in manageable chunks
- Tracks completion percentage for each guideline
- Maintains continuity between sessions
- Supports continuing existing work with special prompts

### 3. Cooperating Agents Workflow (Advanced)

The most sophisticated workflow option transforms the agent farm into a coordinated development team capable of complex, strategic improvements. Amazingly, this powerful feature is implemented entire by means of the prompt file! No actual code is needed to effectuate the system; rather, the LLM (particularly Opus 4) is simply smart enough to understand and reliably implement the system autonomously:

#### Multi-Agent Coordination System

This workflow implements a distributed coordination protocol that allows multiple agents to work on the same codebase simultaneously without conflicts. The system creates a `/coordination/` directory structure in your project:

```
/coordination/
├── active_work_registry.json     # Central registry of all active work
├── completed_work_log.json       # Log of completed tasks  
├── agent_locks/                  # Directory for individual agent locks
│   └── {agent_id}_{timestamp}.lock
└── planned_work_queue.json       # Queue of planned but not started work
```

#### How It Works

1. **Unique Agent Identity**: Each agent generates a unique ID (`agent_{timestamp}_{random_4_chars}`)

2. **Work Claiming Process**: Before starting any work, agents must:
   - Check the active work registry for conflicts
   - Create a lock file claiming specific files and features
   - Register their work plan with detailed scope information
   - Update their status throughout the work cycle

3. **Conflict Prevention**: The lock file system prevents multiple agents from:
   - Modifying the same files simultaneously
   - Implementing overlapping features
   - Creating merge conflicts or breaking changes
   - Duplicating completed work

4. **Smart Work Distribution**: Agents automatically:
   - Select non-conflicting work from available tasks
   - Queue work if their preferred files are locked
   - Handle stale locks (>2 hours old) intelligently
   - Coordinate through descriptive git commits

#### Why This Works Well

This coordination system solves several critical problems:

- **Eliminates Merge Conflicts**: Lock-based file claiming ensures clean parallel development
- **Prevents Wasted Work**: Agents check completed work log before starting
- **Enables Complex Tasks**: Unlike simple bug fixing, agents can tackle strategic improvements
- **Maintains Code Stability**: Functionality testing requirements prevent breaking changes
- **Scales Efficiently**: 20+ agents can work productively without stepping on each other
- **Business Value Focus**: Requires justification and planning before implementation

#### Advanced Features

- **Stale Lock Detection**: Automatically handles abandoned work after 2 hours
- **Emergency Coordination**: Alert system for critical conflicts
- **Progress Transparency**: All agents can see what others are working on
- **Atomic Work Units**: Each agent completes full features before releasing locks
- **Detailed Planning**: Agents must create comprehensive plans before claiming work

#### Best Use Cases

This workflow excels at:
- Large-scale refactoring projects
- Implementing complex architectural changes
- Adding comprehensive type hints across a codebase
- Systematic performance optimizations
- Multi-faceted security improvements
- Feature development requiring coordination

To use this workflow, specify the cooperating agents prompt:
```bash
claude-code-agent-farm \
  --path /project \
  --prompt-file prompts/cooperating_agents_improvement_prompt_for_python_fastapi_postgres.txt \
  --agents 5
```

## 🌐 Technology Stack Support

### Complete List of 34 Supported Tech Stacks

The project includes pre-configured support for:

#### Web Development
1. **Next.js** - TypeScript, React, modern web development
2. **Angular** - Enterprise Angular applications
3. **SvelteKit** - Modern web framework
4. **Remix/Astro** - Full-stack web frameworks
5. **Flutter** - Cross-platform mobile development
6. **Laravel** - PHP web framework
7. **PHP** - General PHP development

#### Systems & Languages
8. **Python** - FastAPI, Django, data science workflows
9. **Rust** - System programming and web applications
10. **Rust CLI** - Command-line tool development
11. **Go** - Web services and cloud-native applications
12. **Java** - Enterprise applications with Spring Boot
13. **C++** - Systems programming and performance-critical applications

#### DevOps & Infrastructure
14. **Bash/Zsh** - Shell scripting and automation
15. **Terraform/Azure** - Infrastructure as Code
16. **Cloud Native DevOps** - Kubernetes, Docker, CI/CD
17. **Ansible** - Infrastructure automation and configuration management
18. **HashiCorp Vault** - Secrets management and policy as code

#### Data & AI
19. **GenAI/LLM Ops** - AI/ML operations and tooling
20. **LLM Dev Testing** - LLM development and testing workflows
21. **LLM Evaluation & Observability** - LLM evaluation and monitoring
22. **Data Engineering** - ETL, analytics, big data
23. **Data Lakes** - Kafka, Snowflake, Spark integration
24. **Polars/DuckDB** - High-performance data processing
25. **Excel Automation** - Python-based Excel automation with Azure
26. **PostgreSQL 17 & Python** - Modern PostgreSQL 17 with FastAPI/SQLModel

#### Specialized Domains
27. **Serverless Edge** - Edge computing and serverless
28. **Kubernetes AI Inference** - AI inference on Kubernetes
29. **Security Engineering** - Security best practices and tooling
30. **Hardware Development** - Embedded systems and hardware design
31. **Unreal Engine** - Game development with Unreal Engine 5
32. **Solana/Anchor** - Blockchain development on Solana
33. **Cosmos** - Cosmos blockchain ecosystem
34. **React Native** - Cross-platform mobile development

Each stack includes:
- Optimized configuration file
- Technology-specific prompts
- Comprehensive best practices guide (31 guides total)
- Appropriate chunk sizes and timing

### Custom Tech Stacks

Create your own configuration:

```json
{
  "comment": "Custom Rust configuration",
  "tech_stack": "rust",
  "problem_commands": {
    "type_check": ["cargo", "check"],
    "lint": ["cargo", "clippy", "--", "-D", "warnings"]
  },
  "best_practices_files": ["./guides/RUST_BEST_PRACTICES.md"],
  "chunk_size": 30,
  "prompt_file": "prompts/rust_prompt.txt",
  "agents": 15,
  "max_agents": 50,
  "auto_restart": true,
  "git_branch": "feature/rust-improvements",
  "git_remote": "origin"
}
```

## ⚙️ Configuration System

### Core Configuration Options

```json
{
  "comment": "Human-readable description",
  "tech_stack": "nextjs",
  "problem_commands": {
    "type_check": ["bun", "run", "type-check"],
    "lint": ["bun", "run", "lint"],
    "test": ["bun", "run", "test"]
  },
  "best_practices_files": ["./best_practices_guides/NEXTJS15_BEST_PRACTICES.md"],
  "chunk_size": 50,
  "agents": 20,
  "max_agents": 50,
  "session": "claude_agents",
  "prompt_file": "prompts/default_prompt_nextjs.txt",
  "auto_restart": true,
  "context_threshold": 20,
  "idle_timeout": 60,
  "max_errors": 3,
  "git_branch": null,
  "git_remote": "origin",
  "tmux_kill_on_exit": true,
  "tmux_mouse": true,
  "stagger": 10.0,
  "wait_after_cc": 15.0,
  "check_interval": 10,
  "skip_regenerate": false,
  "skip_commit": false,
  "no_monitor": false,
  "attach": false,
  "fast_start": false,
  "full_backup": false
}
```

### Key Parameters

- **tech_stack**: Technology identifier (one of 34 supported stacks)
- **problem_commands**: Commands for type-checking, linting, and testing
- **best_practices_files**: Guides to copy to the project
- **chunk_size**: Base lines/changes per agent iteration (dynamically adjusted based on remaining work)
- **prompt_file**: Which prompt template to use (36 available)
- **agents**: Number of agents to run (default: 20)
- **max_agents**: Maximum allowed agents (default: 50)
- **auto_restart**: Enable automatic agent restart
- **context_threshold**: Auto-clear context when it drops below this %
- **git_branch**: Optional specific branch to commit to
- **git_remote**: Remote to push to (default: origin)

### Command Line Options

All configuration options can be overridden via CLI:

```bash
claude-code-agent-farm \
  --path /project \
  --config configs/base.json \
  --agents 10 \
  --chunk-size 30 \
  --auto-restart
```

#### Complete Options Reference

```
Commands:
  doctor                   Run pre-flight verification checks
  monitor-only             Display monitor dashboard (internal use)

Required:
  --path PATH               Project root directory

Agent Configuration:
  --agents N, -n N         Number of agents (default: 20)
  --session NAME, -s NAME  tmux session name (default: claude_agents)
  --chunk-size N           Override config chunk size

Timing:
  --stagger SECONDS        Delay between starting agents (default: 10.0)
  --wait-after-cc SECONDS  Wait time after launching cc (default: 15.0)
  --check-interval SECONDS Health check interval (default: 10)

Features:
  --skip-regenerate        Skip regenerating problems file
  --skip-commit           Skip git commit/push
  --auto-restart          Enable automatic agent restart
  --no-monitor            Just launch agents and exit
  --attach                Attach to tmux after setup

Advanced:
  --prompt-file PATH      Custom prompt file
  --config PATH           JSON configuration file
  --context-threshold N    Auto-clear context when context ≤ N% (default: 20)
  --idle-timeout SECONDS   Mark agent idle after N seconds (default: 60)
  --max-errors N           Disable agent after N errors (default: 3)
  --commit-every N         Commit after every N regeneration cycles
  --tmux-kill-on-exit      Kill tmux session on exit (default: true)
  --no-tmux-kill-on-exit   Keep tmux session running after exit
  --tmux-mouse             Enable tmux mouse support (default: true)
  --no-tmux-mouse          Disable tmux mouse support
  --fast-start             Skip shell prompt detection
  --full-backup            Full backup of Claude settings before start
```

## 📝 Prompt System

### Complete Prompt Inventory (37 Prompts)

The system includes specialized prompts for all workflows and tech stacks:

#### Bug Fixing Prompts (4)
- `default_prompt.txt` - Generic bug fixing
- `default_prompt_nextjs.txt` - Next.js specific
- `default_prompt_python.txt` - Python specific
- `bug_fixing_prompt_for_nextjs.txt` - Advanced Next.js fixing

#### Cooperating Agents Prompts (1)
- `cooperating_agents_improvement_prompt_for_python_fastapi_postgres.txt` - Multi-agent coordination system

#### Best Practices Implementation Prompts (31)
- `default_best_practices_prompt.txt` - Generic implementation
- `continue_best_practices_prompt.txt` - Continue existing work

##### Web Development (7)
- `default_best_practices_prompt_nextjs.txt` - Next.js 15
- `default_best_practices_prompt_angular.txt` - Angular
- `default_best_practices_prompt_sveltekit.txt` - SvelteKit
- `default_best_practices_prompt_remix_astro.txt` - Remix/Astro
- `default_best_practices_prompt_flutter.txt` - Flutter
- `default_best_practices_prompt_laravel.txt` - Laravel
- `default_best_practices_prompt_php.txt` - PHP

##### Systems & Languages (7)
- `default_best_practices_prompt_python.txt` - Python/FastAPI
- `default_best_practices_prompt_rust_web.txt` - Rust web apps
- `default_best_practices_prompt_rust_system.txt` - Rust systems
- `default_best_practices_prompt_rust_cli.txt` - Rust CLI tools
- `default_best_practices_prompt_go.txt` - Go applications
- `default_best_practices_prompt_java.txt` - Java enterprise
- `default_best_practices_prompt_cpp.txt` - C++ systems

##### DevOps & Infrastructure (5)
- `default_best_practices_prompt_bash_zsh.txt` - Shell scripting
- `default_best_practices_prompt_terraform_azure.txt` - IaC
- `default_best_practices_prompt_cloud_native_devops.txt` - DevOps
- `default_best_practices_prompt_ansible.txt` - Ansible automation
- `default_best_practices_prompt_vault.txt` - HashiCorp Vault

##### Data & AI (7)
- `default_best_practices_prompt_genai_llm_ops.txt` - AI/ML ops
- `default_best_practices_prompt_llm_dev_testing.txt` - LLM development
- `default_best_practices_prompt_llm_eval_observability.txt` - LLM evaluation
- `default_best_practices_prompt_data_engineering.txt` - Data pipelines
- `default_best_practices_prompt_data_lakes.txt` - Data lakes
- `default_best_practices_prompt_polars.txt` - Polars/DuckDB
- `default_best_practices_prompt_excel.txt` - Excel automation

##### Specialized (7)
- `default_best_practices_prompt_serverless_edge.txt` - Edge computing
- `default_best_practices_prompt_kubernetes_ai.txt` - Kubernetes AI
- `default_best_practices_prompt_security.txt` - Security engineering
- `default_best_practices_prompt_hardware.txt` - Hardware development
- `default_best_practices_prompt_unreal.txt` - Unreal Engine
- `default_best_practices_prompt_solana.txt` - Solana blockchain
- `default_best_practices_prompt_cosmos.txt` - Cosmos blockchain
- `default_best_practices_prompt_react_native.txt` - React Native

### Variable Substitution

Prompts support dynamic variables:
- `{chunk_size}` - Replaced with configured chunk size

Example in prompt:
```
Work on approximately {chunk_size} improvements at a time...
```

## 🔄 How It Works

### Bug Fixing Workflow

1. **Problem Generation**: Runs type-check, lint, and test commands
2. **Agent Launch**: Starts N agents in tmux panes
3. **Task Distribution**: Each agent selects random problem chunks
4. **Conflict Prevention**: Marks completed problems with [COMPLETED]
5. **Progress Tracking**: Commits changes with rich diff summaries showing file counts and change statistics

### Best Practices Workflow

1. **Guide Distribution**: Copies best practices guides to project
2. **Progress Document**: Agents create/update tracking document
3. **Systematic Implementation**: Works through guidelines incrementally
4. **Accurate Tracking**: Maintains honest completion percentages
5. **Session Continuity**: Progress persists between runs

### Safety Features

1. **Settings Backup**: Automatically backs up Claude settings before starting
   - Creates timestamped backups in `.claude_agent_farm_backups/` in your project
   - Keeps last 10 backups with automatic rotation
   - Enforces 200MB total size limit to prevent disk bloat
   - Full backup option with `--full-backup` flag
   - Reports backup storage status after cleanup
2. **Settings Restore**: Restores from backup if corruption detected
   - Automatic detection of settings errors
   - Seamless restoration during agent startup
3. **File Locking**: Uses file locks to prevent concurrent access issues
   - Lock files in `~/.claude/.agent_farm_launch.lock`
   - 30-second stale lock detection and cleanup
   - Prevents concurrent Claude launches that could corrupt settings
4. **Permission Management**: Automatically fixes file permissions
   - Sets 600 permissions on settings.json
   - Sets 700 permissions on .claude directory
   - Ensures proper file ownership
5. **Atomic Operations**: Uses atomic file operations for safety
6. **Emergency Cleanup**: Handles unexpected exits gracefully
   - Cleans up tmux sessions
   - Removes lock files
   - Deletes state files
7. **Launch Locking**: Prevents concurrent Claude launches with lock files
8. **Adaptive Stagger**: Intelligent launch delays based on success/failure
   - Halves stagger time when previous launch succeeds (faster startup when healthy)
   - Doubles stagger time only when previous launch fails (retains safety)
   - Capped at 60 seconds maximum to prevent excessive delays
9. **Agent Limits**: Enforces max_agents limit (default: 50)
10. **Instance Randomization**: Adds unique seeds to each agent for better work distribution

## 📊 Monitoring Dashboard

The Python script includes a real-time monitoring dashboard that shows:

- **Agent Status**: Working, Idle, Context Low, Error, Disabled
- **Context Usage**: Percentage of agent's context window used with visual warnings
- **Heartbeat Age**: Time since last agent activity pulse (color-coded)
- **Last Activity**: Time since the agent last did something
- **Last Error**: Most recent error message (if any)
- **Session Stats**: Total restarts, uptime, active agents
- **Cycle Count**: Number of work cycles completed

### Context Warnings

Each tmux pane displays context warnings in its title bar:
- ⚠️ **Critical** (≤20%): Agent will clear context soon
- ⚡ **Low** (≤30%): Context running low
- Normal percentage display for healthy levels

### Built-in Dashboard

The monitoring dashboard runs in the tmux controller window:

```
Claude Agent Farm - 14:32:15
┏━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ Agent    ┃ Status     ┃ Cycles ┃ Context  ┃ Runtime      ┃ Heartbeat┃ Errors ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ Pane 00  │ working    │ 2      │ 75%      │ 0:05:23      │ 12s      │ 0      │
│ Pane 01  │ working    │ 2      │ 82%      │ 0:05:19      │ 8s       │ 0      │
│ Pane 02  │ idle       │ 3      │ 45%      │ 0:05:15      │ 45s      │ 0      │
└──────────┴────────────┴────────┴──────────┴──────────────┴──────────┴────────┘
```

### Viewing Options

```bash
# Use the viewer script
./view_agents.sh

# Direct tmux commands
tmux attach -t claude_agents
tmux attach -t claude_agents:controller  # Dashboard only
```

### Context Reset Macro

Press `Ctrl+R` from any tmux window to broadcast the `/clear` command to all agents simultaneously. This frees up context across all agents with a single keystroke, useful when multiple agents are running low on context.

### Agent States

- 🟡 **starting** - Agent initializing
- 🟢 **working** - Actively processing
- 🔵 **ready** - Waiting for input
- 🟡 **idle** - Completed work
- 🔴 **error** - Problem detected
- ⚫ **unknown** - State unclear

### Auto-Restart Features

When `--auto-restart` is enabled:
- Monitors agent health continuously via heartbeat files
- Restarts agents that hit errors, go idle, or have stale heartbeats (>2 minutes)
- Monitors context percentage and clears context when below threshold
- Adaptive idle timeout adjusts based on agent work patterns
  - Tracks cycle completion times across all agents
  - Sets timeout to 3× median cycle time (bounded 30s-600s)
  - Prevents false positives on complex tasks
  - Speeds up detection on simple tasks
- Implements exponential backoff to prevent restart loops
  - Initial wait: 10 seconds
  - Doubles with each restart (max 5 minutes)
- Tracks restart count per agent
- Disables agents after max_errors threshold

### Monitor State File

The system writes monitor state to `.claude_agent_farm_state.json` in the project directory. This file contains:
- Agent statuses and health metrics
- Session information
- Runtime statistics

Structure:
```json
{
  "session": "claude_agents",
  "num_agents": 20,
  "agents": {
    "0": {
      "status": "working",
      "start_time": "2024-01-15T10:30:00",
      "last_activity": "2024-01-15T10:35:00",
      "last_restart": null,
      "cycles": 2,
      "last_context": 75,
      "errors": 0,
      "restart_count": 0
    }
  },
  "start_time": "2024-01-15T10:30:00",
  "timestamp": "2024-01-15T10:35:00"
}
```

External tools can read this file to monitor the farm's progress.

### HTML Run Reports

At the end of each run, the system generates a comprehensive HTML report with:

- **Run Summary**: Duration, agents used, problems fixed, commits made
- **Agent Performance**: Individual agent statistics including cycles, context usage, errors, and restarts
- **Configuration Details**: All settings used for the run
- **Visual Formatting**: Rich HTML output with syntax highlighting and dark theme

Reports are saved as `agent_farm_report_YYYYMMDD_HHMMSS.html` in the project directory.

Features:
- Single-file HTML with inline styles (no external dependencies)
- Professional dark theme optimized for code review
- Sortable tables with color-coded status indicators
- Complete run statistics for documentation or pull requests
- Automatic generation on graceful shutdown

## 💡 Usage Examples

### Quick Test Run
```bash
# 5 agents, skip git operations
claude-code-agent-farm --path /project -n 5 --skip-regenerate --skip-commit
```

### Production Bug Fixing
```bash
# Full run with Python project
claude-code-agent-farm \
  --path /python/project \
  --config configs/python_uv_config.json \
  --agents 15 \
  --auto-restart
```

### Best Practices Implementation
```bash
# Systematic improvements
claude-code-agent-farm \
  --path /nextjs/project \
  --config configs/nextjs_best_practices_config.json \
  --agents 10
```

### Incremental Commits
```bash
# Commit progress every 5 cycles
claude-code-agent-farm \
  --path /project \
  --config configs/python_config.json \
  --agents 20 \
  --commit-every 5 \
  --auto-restart
```

### Custom Configuration
```bash
# Override config settings
claude-code-agent-farm \
  --path /project \
  --config configs/base.json \
  --chunk-size 25 \
  --context-threshold 15 \
  --idle-timeout 120
```

### Headless Operation
```bash
# Run without monitoring (for CI/CD)
claude-code-agent-farm \
  --path /project \
  --config configs/ci-config.json \
  --no-monitor \
  --auto-restart
```

### Specialized Stacks
```bash
# Angular development
claude-code-agent-farm \
  --path /angular/project \
  --config configs/angular_config.json

# Blockchain development
claude-code-agent-farm \
  --path /solana/project \
  --config configs/solana_anchor_config.json

# Data engineering
claude-code-agent-farm \
  --path /data/project \
  --config configs/polars_duckdb_config.json
```

### Cooperating Agents Mode
```bash
# Advanced multi-agent coordination for complex improvements
claude-code-agent-farm \
  --path /project \
  --prompt-file prompts/cooperating_agents_improvement_prompt_for_python_fastapi_postgres.txt \
  --agents 20 \
  --auto-restart
```

## 🚨 Troubleshooting

### Common Issues

#### Agents not starting
- Verify `cc` alias: `alias | grep cc`
- Test Claude Code manually: `cc`
- Check API key configuration
- Increase `--wait-after-cc` timing
- Use `--full-backup` flag if settings corruption suspected

#### Configuration errors
- Validate JSON syntax
- Ensure all paths are correct
- Check command availability (mypy, ruff, etc.)
- Verify best practices guides exist

#### Resource issues
- Each agent uses ~500MB RAM
- Reduce agent count if needed
- Monitor with `htop`
- Check available disk space for logs
- Respect max_agents limit (default: 50)

#### Settings corruption
- System automatically backs up settings
- Restores from backup on error detection
- Manual restore: Check `~/.claude/backups/`
- Use `--full-backup` for comprehensive backup

### Debug Features

- **State File**: Check `.claude_agent_farm_state.json` for agent status
- **Heartbeat Files**: Monitor `.heartbeats/agent*.heartbeat` for activity tracking
- **Lock Files**: Look for `.agent_farm_launch.lock` in `~/.claude/`
- **Backup Directory**: `.claude_agent_farm_backups/` in project contains settings backups
- **Pre-flight Check**: Run `claude-code-agent-farm doctor` to diagnose issues
- **Emergency Cleanup**: Ctrl+C triggers graceful shutdown
  - First Ctrl+C: Graceful shutdown with agent cleanup
  - Second Ctrl+C within 3 seconds: Force kills tmux session
  - Automatically cleans up state files and locks
- **Manual tmux**: `tmux kill-session -t claude_agents` to force cleanup

## 📁 Project Structure

```
claude_code_agent_farm/
├── claude_code_agent_farm.py    # Main orchestrator
├── view_agents.sh               # Tmux viewer utility
├── setup.sh                     # Automated setup
├── pyproject.toml              # Python project configuration
├── uv.lock                     # Locked dependencies
├── .envrc                      # direnv configuration
├── .gitignore                  # Git ignore patterns
├── configs/                     # 33 configuration files
│   ├── nextjs_config.json      # Next.js bug fixing
│   ├── python_config.json      # Python bug fixing
│   ├── python_uv_config.json   # Python with uv
│   ├── nextjs_best_practices_config.json
│   ├── angular_config.json     # Angular development
│   ├── flutter_config.json     # Flutter mobile
│   ├── rust_system_config.json # Rust systems programming
│   ├── rust_webapps_config.json # Rust web apps
│   ├── rust_cli_config.json    # Rust CLI tools
│   ├── go_webapps_config.json  # Go web development
│   ├── java_enterprise_config.json # Java enterprise
│   ├── cpp_systems_config.json # C++ systems
│   ├── php_config.json         # PHP development
│   ├── laravel_config.json     # Laravel framework
│   ├── sveltekit2_config.json  # SvelteKit framework
│   ├── remix_astro_config.json # Remix/Astro frameworks
│   ├── bash_zsh_config.json    # Shell scripting
│   ├── terraform_azure_config.json # Infrastructure as Code
│   ├── cloud_native_devops_config.json # DevOps tools
│   ├── ansible_config.json     # Ansible automation
│   ├── vault_config.json       # HashiCorp Vault
│   ├── genai_llm_ops_config.json # AI/ML operations
│   ├── data_engineering_config.json # Data pipelines
│   ├── data_lakes_config.json  # Kafka/Snowflake/Spark
│   ├── polars_duckdb_config.json # Data processing
│   ├── excel_automation_config.json # Excel automation
│   ├── serverless_edge_config.json # Edge computing
│   ├── security_engineering_config.json # Security
│   ├── hardware_dev_config.json # Hardware development
│   ├── unreal_engine_config.json # Game development
│   ├── solana_anchor_config.json # Solana blockchain
│   ├── cosmos_blockchain_config.json # Cosmos blockchain
│   └── sample.json             # Example configuration
├── prompts/                     # 37 prompt templates
│   ├── Bug fixing prompts (4)
│   ├── Cooperating agents prompts (1)
│   ├── Generic best practices prompts (2)
│   └── Stack-specific best practices prompts (30)
├── best_practices_guides/       # 35 best practices documents
│   ├── Web Development (7 guides)
│   ├── Systems & Languages (7 guides)
│   ├── DevOps & Infrastructure (5 guides)
│   ├── Data & AI (6 guides)
│   └── Specialized Domains (6 guides)
├── tool_setup_scripts/          # 24 development environment setup scripts
│   ├── setup.sh                # Interactive menu
│   ├── common_utils.sh         # Shared utilities
│   ├── README.md              # Setup scripts documentation
│   ├── Web Development (4 scripts)
│   ├── Systems & Languages (3 scripts)
│   ├── DevOps & Infrastructure (3 scripts)
│   └── Data & AI (3 scripts)
└── __pycache__/                # Python cache (gitignored)
```

## 🔧 Advanced Topics

### Creating Custom Workflows

1. **Define your tech stack config** (see 34 examples)
2. **Create appropriate prompts** (follow 37 existing patterns)
3. **Add best practices guides** (optional, see 35 examples)
4. **Configure problem commands** (type-check, lint, test)
5. **Set appropriate chunk sizes** (20-75 based on complexity)
6. **Test with small agent counts first**

### Scaling Considerations

- Start small (5-10 agents) and scale up
- Maximum 50 agents by default (configurable via `max_agents`)
- Increase stagger time for many agents
- Consider running in batches for 50+ agents
- Use `--no-monitor` for headless operation
- Monitor system resources (RAM, CPU)
- Adjust chunk sizes based on performance

### Integration with CI/CD

```bash
#!/bin/bash
# Automated code improvement script
claude-code-agent-farm \
  --path $PROJECT_PATH \
  --config configs/ci-config.json \
  --no-monitor \
  --auto-restart \
  --skip-commit \
  --agents 10
```

### Custom Git Workflows

Configure custom git branches and remotes in your config:

```json
{
  "git_branch": "feature/ai-improvements",
  "git_remote": "upstream",
  "skip_commit": false
}
```

### Performance Tuning

- **Chunk Size**: Automatically adjusts based on remaining work
  - Base sizes by stack: Python (50), Next.js (50), Rust (30), Go (40), Java (35)
  - Dynamic formula: `max(10, total_lines / agents / 2)`
  - Prevents agents from running out of work or doing trivial tasks
- **Stagger Time**: Adaptive timing based on launch success
  - Default 10s baseline prevents settings corruption
  - Automatically halves when previous launch succeeds (minimum: baseline)
  - Doubles only when previous launch fails (maximum: 60s)
  - Results in faster startup when system is healthy
- **Context Threshold**: Lower values (15-20%) clear context sooner
- **Idle Timeout**: Adjust based on task complexity
- **Check Interval**: Balance between responsiveness and CPU usage
- **Heartbeat Monitoring**: Detects stuck agents (>2 minutes since last pulse)
- **Max Agents**: Increase beyond 50 for powerful systems
- **Wait After CC**: Default 15s ensures Claude is fully ready
  - Increase if seeing startup failures
- **Incremental Commits**: Use `--commit-every N` to commit progress periodically
  - Prevents giant diffs that are hard to review
  - Tracks minimum cycles across all agents for consistency

### Advanced Features

#### Interruptible Operations
- All long-running operations can be interrupted with Ctrl+C
- Graceful shutdown preserves work in progress
- Emergency cleanup on unexpected exits

#### Smart Error Detection
- Detects multiple error conditions:
  - Settings corruption
  - Authentication failures  
  - Welcome/setup screens
  - Command not found errors
  - Parse errors (TypeError, SyntaxError, JSONDecodeError)
  - Login prompts and API key issues
- Automatic recovery attempts before disabling agents
- Preserves other working agents during recovery

#### Variable Substitution in Prompts
- `{chunk_size}` - Replaced with configured chunk size
- Supports regex patterns for flexible prompt templates

#### Session Name Validation
- Only allows letters, numbers, hyphens, and underscores
- Prevents tmux errors from invalid characters

#### Shell Prompt Detection
- Intelligently waits for shell prompts before sending commands
- `--fast-start` flag skips prompt detection for faster launches
- Handles both bash and zsh prompts
- Robust, multi-layer readiness check before sending commands:
  1. Passive heuristics that recognise common prompt symbols and current directory names
  2. Active probe fallback that sends a one-off `echo` with a unique marker and waits for the response – works even with minimal or heavily customised prompts
  Works seamlessly with bash, zsh, fish, and other POSIX-compatible shells
  `--fast-start` flag remains available to skip detection entirely for advanced users who want the quickest possible launch

#### User Confirmations
- Interruptible confirmation prompts (Ctrl+C uses default)
- Safe defaults for all destructive operations
- Clear messaging for all user interactions

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests if applicable
4. Update documentation
5. Submit a pull request

### Adding New Tech Stacks

1. Create config file in `configs/` (34 examples to follow)
2. Add prompts in `prompts/` (37 examples available)
3. Write best practices guide in `best_practices_guides/` (35 examples)
4. Add setup script in `tool_setup_scripts/` (15 examples)
5. Test thoroughly with various project types
6. Update this README with your addition

## 👨‍💻 Author

Created by Jeffrey Emanuel (jeffrey.emanuel@gmail.com)

## 📄 License

MIT License (with OpenAI/Anthropic Rider) — see [LICENSE](LICENSE) file

## ⚠️ Important Notes

- **Always backup your code** before running
- **Review changes** before committing
- **Start with few agents** to test
- **Monitor first runs** to ensure proper behavior
- **Check resource usage** for large agent counts
- **Verify cc alias** is properly configured
- **Ensure git is configured** with proper credentials
- **Respect agent limits** (default max: 50)
- **Claude settings** are automatically backed up and restored
- **Lock files** prevent concurrent launches and corruption
- **State files** enable external monitoring tools

## 🔍 Additional Resources

### Monitoring Tools
- Monitor state file (`.claude_agent_farm_state.json`) for external integrations
- Heartbeat files (`.heartbeats/agent*.heartbeat`) track agent activity
- tmux pane titles show real-time context warnings
- tmux session logs for debugging agent issues
- Git commit history for tracking improvements

### Recovery Options
- Manual settings restore from `.claude_agent_farm_backups/` in your project
- Lock file cleanup: `rm ~/.claude/.agent_farm_launch.lock`
- Emergency session cleanup: `tmux kill-session -t claude_agents`
- View HTML run reports from previous sessions for debugging

### Performance Optimization
- Use SSDs for better file I/O performance
- Allocate 500MB RAM per agent
- Consider network bandwidth for API calls
- Monitor CPU usage with `htop` during runs

---

*Happy farming! 🚜 May your code be clean and your agents productive.*

## 📊 Quick Reference

### Tech Stack Support Summary

| Category | Count | Examples |
|----------|-------|----------|
| Web Development | 8 | Next.js, Angular, Flutter, Laravel, React Native |
| Systems & Languages | 7 | Python, Rust, Go, Java, C++ |
| DevOps & Infrastructure | 6 | Terraform, Kubernetes, Ansible |
| Data & AI | 8 | GenAI/LLM, Data Lakes, PostgreSQL 17, Polars |
| Specialized | 5 | Security, Hardware, Blockchain |
| **Total** | **34** | |

### Resource Summary

| Resource | Count |
|----------|-------|
| Configuration Files | 37 |
| Prompt Templates | 37 |
| Best Practices Guides | 35 |
| Tool Setup Scripts | 24 |