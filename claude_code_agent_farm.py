#!/usr/bin/env python3
"""
Claude Code Agent Farm - Hybrid Orchestrator
Combines simplicity with robust monitoring and automatic agent management
"""

import contextlib
import fcntl
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from datetime import datetime
from pathlib import Path
from random import randint
from typing import Any, Dict, List, Optional, Tuple, Union

import typer
from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)
from rich.prompt import Confirm
from rich.table import Table

app = typer.Typer(
    rich_markup_mode="rich",
    help="Orchestrate multiple Claude Code agents for parallel work using tmux",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console(stderr=True)  # Use stderr for progress/info so stdout remains clean

# ─────────────────────────────── Configuration ────────────────────────────── #


def interruptible_confirm(message: str, default: bool = False) -> bool:
    """Confirmation prompt that returns default on KeyboardInterrupt"""
    try:
        return Confirm.ask(message, default=default)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted - using default response[/yellow]")
        return default




# ─────────────────────────────── Constants ────────────────────────────────── #

MONITOR_STATE_FILE = ".claude_agent_farm_state.json"

# ─────────────────────────────── Helper Functions ─────────────────────────── #


def run(cmd: str, *, check: bool = True, quiet: bool = False, capture: bool = False) -> Tuple[int, str, str]:
    """Execute shell command with optional output capture

    When capture=False, output is streamed to terminal unless quiet=True
    When capture=True, output is captured and returned
    """
    if not quiet:
        console.log(cmd, style="cyan")

    # Parse command for shell safety when possible
    cmd_arg: Union[str, List[str]]
    try:
        # Try to parse as a list of arguments for safer execution
        cmd_list = shlex.split(cmd)
        use_shell = False
        cmd_arg = cmd_list
    except ValueError:
        # Fall back to shell=True for complex commands with pipes, redirects, etc.
        cmd_list = []  # Not used when shell=True
        use_shell = True
        cmd_arg = cmd

    if capture:
        result = subprocess.run(cmd_arg, shell=use_shell, capture_output=True, text=True, check=check)
        return result.returncode, result.stdout or "", result.stderr or ""
    else:
        # Stream output to terminal when not capturing
        # Preserve stderr even in quiet-mode so that exceptions contain detail
        if quiet:
            result = subprocess.run(cmd_arg, shell=use_shell, capture_output=True, text=True, check=check)
            return result.returncode, result.stdout or "", result.stderr or ""
        stdout_pipe = None
        stderr_pipe = subprocess.STDOUT
        try:
            result = subprocess.run(
                cmd_arg, shell=use_shell, check=check, stdout=stdout_pipe, stderr=stderr_pipe, text=True
            )
            return result.returncode, "", ""
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Command failed with exit code {e.returncode}: {cmd}[/red]")
            raise


def line_count(file_path: Path) -> int:
    """Count lines in a file"""
    try:
        # Try UTF-8 first, then fall back to latin-1
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return sum(1 for _ in f)
        except UnicodeDecodeError:
            # Try common encodings
            for encoding in ["latin-1", "cp1252", "iso-8859-1"]:
                try:
                    with file_path.open("r", encoding=encoding) as f:
                        return sum(1 for _ in f)
                except UnicodeDecodeError:
                    continue
            # Last resort: ignore errors
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not count lines in {file_path}: {e}[/yellow]")
        return 0


def tmux_send(target: str, data: str, enter: bool = True, update_heartbeat: bool = True) -> None:
    """Send keystrokes to a tmux pane (binary-safe)"""
    max_retries = 3
    base_delay = 0.5

    for attempt in range(max_retries):
        try:
            if data:
                # Use tmux buffer API for robustness with large payloads
                # Create a temporary file with the data to avoid shell-quoting issues
                import os
                import tempfile
                import uuid

                with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
                    tmp.write(data)
                    tmp_path = tmp.name

                buf_name = f"agentfarm_{uuid.uuid4().hex[:8]}"

                try:
                    # Load the data into a tmux buffer
                    run(f"tmux load-buffer -b {buf_name} {shlex.quote(tmp_path)}", quiet=True)
                    # Paste the buffer into the target pane and delete the buffer (-d)
                    run(f"tmux paste-buffer -d -b {buf_name} -t {target}", quiet=True)
                finally:
                    # Clean up temp file
                    with contextlib.suppress(FileNotFoundError):
                        os.unlink(tmp_path)

                # CRITICAL: Small delay between pasting and Enter for Claude Code
                if enter:
                    time.sleep(0.2)

            if enter:
                run(f"tmux send-keys -t {target} C-m", quiet=True)
            
            # Update heartbeat if requested (default True)
            if update_heartbeat:
                # Extract agent ID from target (format: session:window.pane)
                try:
                    pane_id = target.split('.')[-1]
                    agent_id = int(pane_id)
                    heartbeat_file = Path(".heartbeats") / f"agent{agent_id:02d}.heartbeat"
                    if heartbeat_file.parent.exists():
                        heartbeat_file.write_text(datetime.now().isoformat())
                except (ValueError, IndexError, OSError):
                    # Silently ignore heartbeat errors
                    pass
            break
        except subprocess.CalledProcessError:
            if attempt < max_retries - 1:
                # Exponential backoff: 0.5s, 1s, 2s
                time.sleep(base_delay * (2**attempt))
            else:
                raise


def tmux_capture(target: str) -> str:
    """Capture content from a tmux pane"""
    max_retries = 3

    for attempt in range(max_retries):
        try:
            _, stdout, _ = run(f"tmux capture-pane -t {target} -p", quiet=True, capture=True)
            return stdout
        except subprocess.CalledProcessError:
            if attempt < max_retries - 1:
                time.sleep(0.2)
            else:
                # Return empty string on persistent failure
                return ""
    return ""


# ─────────────────────────────── Agent Monitor ────────────────────────────── #


class AgentMonitor:
    """Monitors Claude Code agents for health and performance"""

    def __init__(
        self,
        session: str,
        num_agents: int,
        pane_mapping: Dict[int, str],
        context_threshold: int = 20,
        idle_timeout: int = 60,
        max_errors: int = 3,
        project_path: Optional[Path] = None,
    ):
        self.session = session
        self.num_agents = num_agents
        self.pane_mapping = pane_mapping
        self.agents: Dict[int, Dict] = {}
        self.running = True
        self.start_time = datetime.now()
        self.context_threshold = context_threshold
        self.idle_timeout = idle_timeout
        self.base_idle_timeout = idle_timeout  # Keep original value as base
        self.max_errors = max_errors
        self.project_path = project_path
        
        # Cycle time tracking for adaptive timeout
        self.cycle_times: List[float] = []
        self.max_cycle_history = 20  # Keep last 20 cycle times
        
        # Setup heartbeats directory
        self.heartbeats_dir: Optional[Path] = None
        if self.project_path:
            self.heartbeats_dir = self.project_path / ".heartbeats"
            self.heartbeats_dir.mkdir(exist_ok=True)
            # Clean up any old heartbeat files
            for hb_file in self.heartbeats_dir.glob("agent*.heartbeat"):
                hb_file.unlink(missing_ok=True)

        # Initialize agent tracking
        for i in range(num_agents):
            self.agents[i] = {
                "status": "starting",
                "start_time": datetime.now(),
                "cycles": 0,
                "last_context": 100,
                "errors": 0,
                "last_activity": datetime.now(),
                "restart_count": 0,
                "last_restart": None,
                "last_heartbeat": None,
                "cycle_start_time": None,
            }

    def calculate_adaptive_timeout(self) -> int:
        """Calculate adaptive idle timeout based on median cycle time"""
        if len(self.cycle_times) < 3:
            # Not enough data, use base timeout
            return self.base_idle_timeout
        
        # Calculate median cycle time
        sorted_times = sorted(self.cycle_times)
        median_time = sorted_times[len(sorted_times) // 2]
        
        # Set timeout to 3x median cycle time, but within reasonable bounds
        adaptive_timeout = int(median_time * 3)
        
        # Enforce minimum and maximum bounds
        min_timeout = 30  # At least 30 seconds
        max_timeout = 600  # At most 10 minutes
        
        adaptive_timeout = max(min_timeout, min(adaptive_timeout, max_timeout))
        
        # Only update if significantly different from current (>20% change)
        if abs(adaptive_timeout - self.idle_timeout) / self.idle_timeout > 0.2:
            console.print(f"[dim]Adjusting idle timeout: {self.idle_timeout}s → {adaptive_timeout}s (median cycle: {median_time:.1f}s)[/dim]")
            self.idle_timeout = adaptive_timeout
        
        return self.idle_timeout
    
    def detect_context_percentage(self, content: str) -> Optional[int]:
        """Extract context percentage from pane content"""
        # Try multiple patterns for robustness
        patterns = [
            r"Context left until\s*auto-compact:\s*(\d+)%",
            r"Context remaining:\s*(\d+)%",
            r"(\d+)%\s*context\s*remaining",
            r"Context:\s*(\d+)%",
        ]

        # Safety check for empty content
        if not content:
            return None

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def is_claude_ready(self, content: str) -> bool:
        """Check if Claude Code is ready for input"""
        # Multiple possible indicators that Claude is ready
        ready_indicators = [
            "Welcome to Claude Code!" in content,  # Welcome message
            ("│ > Try" in content),  # The prompt box with suggestion
            ("❯ Try " in content),  # The prompt box with suggestion
            ("? for shortcuts" in content),  # Shortcuts hint at bottom
            ("╰─" in content and "│ >" in content),  # Box structure with prompt
            ("/help for help" in content),  # Help text in welcome message
            ("cwd:" in content and "Welcome to Claude" in content),  # Working directory shown
            ("Bypassing Permissions" in content and "│ >" in content),  # May appear with prompt
            ("│ >" in content and "─╯" in content),  # Prompt box bottom border
        ]
        return any(ready_indicators)

    def is_claude_working(self, content: str) -> bool:
        """Check if Claude Code is actively working"""
        indicators = ["✻ Pontificating", "● Bash(", "✻ Running", "✻ Thinking", "esc to interrupt"]
        return any(indicator in content for indicator in indicators)

    def has_welcome_screen(self, content: str) -> bool:
        """Check if Claude Code is showing the welcome/setup screen"""
        welcome_indicators = [
            # Setup/onboarding screens only
            "Choose the text style",
            "Choose your language",
            "Let's get started",
            "run /theme",
            "Dark mode✔",
            "Light mode",
            "colorblind-friendly",
            # Remove "Welcome to Claude Code" as it appears when ready
        ]
        return any(indicator in content for indicator in welcome_indicators)

    def has_settings_error(self, content: str) -> bool:
        """Check for settings corruption"""
        # First check if Claude is actually ready (avoid false positives)
        if self.is_claude_ready(content):
            return False
            
        error_indicators = [
            # Login/auth prompts
            "Select login method:",
            "Claude account with subscription",
            "Sign in to Claude",
            "Log in to Claude",
            "Enter your API key",
            "API key",
            # Configuration errors
            "Configuration error",
            "Settings corrupted",
            "Invalid API key",
            "Authentication failed",
            "Rate limit exceeded",
            "Unauthorized",
            "Permission denied",
            "Failed to load configuration",
            "Invalid configuration",
            "Error loading settings",
            "Settings file is corrupted",
            "Failed to parse settings",
            "Invalid settings",
            "Corrupted settings",
            "Config corrupted",
            "configuration is corrupted",
            "Unable to load settings",
            "Error reading settings",
            "Settings error",
            "config error",
            # Parse errors
            "TypeError",
            "SyntaxError",
            "JSONDecodeError",
            "ParseError",
            # Other login-related text
            "Choose your login method",
            "Continue with Claude account",
            "I have a Claude account",
            "Create account",
        ]
        return any(indicator in content for indicator in error_indicators)

    def check_agent(self, agent_id: int) -> Dict:
        """Check status of a single agent"""
        pane_target = self.pane_mapping.get(agent_id)
        if not pane_target:
            console.print(f"[red]Error: No pane mapping found for agent {agent_id}[/red]")
            return self.agents[agent_id]

        content = tmux_capture(pane_target)

        agent = self.agents[agent_id]

        # Update context percentage
        context = self.detect_context_percentage(content)
        if context is not None:
            agent["last_context"] = context

        # Check for errors
        if self.has_settings_error(content):
            agent["status"] = "error"
            agent["errors"] += 1
        else:
            # Store previous status to detect transitions
            prev_status = agent.get("status", "unknown")
            
            # Update status based on activity
            if self.is_claude_working(content):
                # If transitioning to working, record cycle start time
                if prev_status != "working" and agent["cycle_start_time"] is None:
                    agent["cycle_start_time"] = datetime.now()
                
                agent["status"] = "working"
                agent["last_activity"] = datetime.now()
                # Update heartbeat when agent is actively working
                self._update_heartbeat(agent_id)
            elif self.is_claude_ready(content):
                # If transitioning from working to ready, record cycle time
                if prev_status == "working" and agent["cycle_start_time"] is not None:
                    cycle_time = (datetime.now() - agent["cycle_start_time"]).total_seconds()
                    self.cycle_times.append(cycle_time)
                    
                    # Keep only recent cycle times
                    if len(self.cycle_times) > self.max_cycle_history:
                        self.cycle_times.pop(0)
                    
                    # Update adaptive timeout
                    self.calculate_adaptive_timeout()
                    
                    # Reset cycle start time
                    agent["cycle_start_time"] = None
                    
                    # Increment cycle count
                    agent["cycles"] += 1
                
                # Check if idle for too long
                idle_time = (datetime.now() - agent["last_activity"]).total_seconds()
                if idle_time > self.idle_timeout:
                    agent["status"] = "idle"
                else:
                    agent["status"] = "ready"
                    # Update heartbeat when agent is ready (not idle)
                    self._update_heartbeat(agent_id)
            else:
                agent["status"] = "unknown"
        
        # Update tmux pane title with context information
        self._update_pane_title(agent_id, agent)

        return agent
    
    def _update_pane_title(self, agent_id: int, agent: Dict) -> None:
        """Update tmux pane title with agent status and context percentage"""
        pane_target = self.pane_mapping.get(agent_id)
        if not pane_target:
            return
        
        # Build title with context warning
        context = agent["last_context"]
        status = agent["status"]
        
        # Create context indicator with warning colors
        if context <= self.context_threshold:
            context_str = f"⚠️ {context}%"
        elif context <= 30:
            context_str = f"⚡{context}%"
        else:
            context_str = f"{context}%"
        
        # Status emoji
        status_emoji = {
            "working": "🔧",
            "ready": "✅",
            "idle": "💤",
            "error": "❌",
            "starting": "🚀",
            "unknown": "❓"
        }.get(status, "")
        
        # Build title
        title = f"[{agent_id:02d}] {status_emoji} Context: {context_str}"
        
        # Set pane title
        with contextlib.suppress(subprocess.CalledProcessError):
            run(f"tmux select-pane -t {pane_target} -T {shlex.quote(title)}", quiet=True)

    def _update_heartbeat(self, agent_id: int) -> None:
        """Update heartbeat file for an agent"""
        if not self.heartbeats_dir:
            return
        
        heartbeat_file = self.heartbeats_dir / f"agent{agent_id:02d}.heartbeat"
        try:
            # Write current timestamp to heartbeat file
            heartbeat_file.write_text(datetime.now().isoformat())
            self.agents[agent_id]["last_heartbeat"] = datetime.now()
        except Exception:
            # Silently ignore heartbeat write errors
            pass
    
    def _check_heartbeat_age(self, agent_id: int) -> Optional[float]:
        """Check age of heartbeat file in seconds"""
        if not self.heartbeats_dir:
            return None
        
        heartbeat_file = self.heartbeats_dir / f"agent{agent_id:02d}.heartbeat"
        if not heartbeat_file.exists():
            return None
        
        try:
            mtime = heartbeat_file.stat().st_mtime
            age = time.time() - mtime
            return age
        except Exception:
            return None
    
    def needs_restart(self, agent_id: int) -> Optional[str]:
        """Determine if an agent needs to be restarted and why

        Returns:
            None  - no restart needed
            'context' - context nearly exhausted, use /clear
            'error' - encountered errors or heartbeat stalled, full restart
            'idle' - idle for too long, full restart
        """
        agent = self.agents[agent_id]

        # Stalled heartbeat indicates the pane is likely hung
        heartbeat_age = self._check_heartbeat_age(agent_id)
        if heartbeat_age is not None and heartbeat_age > 120:
            console.print(f"[yellow]Agent {agent_id} heartbeat is {heartbeat_age:.0f}s old[/yellow]")
            return "error"

        # Low-context can often be resolved with /clear instead of a full restart
        if agent["last_context"] <= self.context_threshold:
            return "context"

        # Hard failures or repeated errors → full restart
        if agent["status"] == "error" or agent["errors"] >= self.max_errors:
            return "error"

        # Prolonged idleness → full restart so it picks up new work
        if agent["status"] == "idle":
            return "idle"

        return None

    def get_status_table(self) -> Table:
        """Generate status table for all agents"""
        table = Table(
            title=f"Claude Agent Farm - {datetime.now().strftime('%H:%M:%S')}",
            box=box.ROUNDED,  # Use rounded corners for status tables
        )

        table.add_column("Agent", style="cyan", width=8)
        table.add_column("Status", style="green", width=10)
        table.add_column("Cycles", style="yellow", width=6)
        table.add_column("Context", style="magenta", width=8)
        table.add_column("Runtime", style="blue", width=12)
        table.add_column("Heartbeat", style="cyan", width=8)
        table.add_column("Errors", style="red", width=6)

        for agent_id in sorted(self.agents.keys()):
            agent = self.agents[agent_id]
            runtime = str(datetime.now() - agent["start_time"]).split(".")[0]

            status_style = {
                "working": "[green]",
                "ready": "[cyan]",
                "idle": "[yellow]",
                "error": "[red]",
                "starting": "[yellow]",
                "unknown": "[dim]",
            }.get(agent["status"], "")
            
            # Get heartbeat age
            heartbeat_age = self._check_heartbeat_age(agent_id)
            if heartbeat_age is None:
                heartbeat_str = "---"
            elif heartbeat_age < 30:
                heartbeat_str = f"[green]{heartbeat_age:.0f}s[/green]"
            elif heartbeat_age < 60:
                heartbeat_str = f"[yellow]{heartbeat_age:.0f}s[/yellow]"
            else:
                heartbeat_str = f"[red]{heartbeat_age:.0f}s[/red]"

            table.add_row(
                f"Pane {agent_id:02d}",
                f"{status_style}{agent['status']}[/]",
                str(agent["cycles"]),
                f"{agent['last_context']}%",
                runtime,
                heartbeat_str,
                str(agent["errors"]),
            )

        return table


# ─────────────────────────────── Main Orchestrator ────────────────────────── #


class ClaudeAgentFarm:
    def __init__(
        self,
        path: str,
        agents: int = 6,
        session: str = "claude_agents",
        stagger: float = 10.0,  # Increased from 4.0 to prevent settings clobbering
        wait_after_cc: float = 15.0,  # Increased from 8.0 to ensure Claude Code is fully ready
        check_interval: int = 10,
        skip_regenerate: bool = False,
        skip_commit: bool = False,
        auto_restart: bool = False,
        no_monitor: bool = False,
        attach: bool = False,
        prompt_file: Optional[str] = None,
        config: Optional[str] = None,
        context_threshold: int = 20,
        idle_timeout: int = 60,
        max_errors: int = 3,
        tmux_kill_on_exit: bool = True,
        tmux_mouse: bool = True,
        fast_start: bool = False,
        full_backup: bool = False,
        commit_every: Optional[int] = None,
    ):
        # Store all parameters
        self.path = path
        self.agents = agents
        self.session = session
        self.stagger = stagger
        self.wait_after_cc = wait_after_cc
        self.check_interval = check_interval
        self.skip_regenerate = skip_regenerate
        self.skip_commit = skip_commit
        self.auto_restart = auto_restart
        self.no_monitor = no_monitor
        self.attach = attach
        self.prompt_file = prompt_file
        self.config = config
        self.context_threshold = context_threshold
        self.idle_timeout = idle_timeout
        self.max_errors = max_errors
        self.tmux_kill_on_exit = tmux_kill_on_exit
        self.tmux_mouse = tmux_mouse
        self.fast_start = fast_start
        self.full_backup = full_backup
        self.commit_every = commit_every

        # Initialize pane mapping
        self.pane_mapping: Dict[int, str] = {}
        
        # Track regeneration cycles for incremental commits
        self.regeneration_cycles = 0
        
        # Track run statistics for reporting
        self.run_start_time = datetime.now()
        self.total_problems_fixed = 0
        self.total_commits_made = 0
        self.agent_restart_count = 0

        # Validate session name (tmux has restrictions)
        if not re.match(r"^[a-zA-Z0-9_-]+$", self.session):
            raise ValueError(
                f"Invalid tmux session name '{self.session}'. Use only letters, numbers, hyphens, and underscores."
            )

        # Apply config file if provided
        if config:
            self._load_config(config)

        # Validate agent count
        if self.agents > getattr(self, "max_agents", 50):
            raise ValueError(f"Agent count {self.agents} exceeds maximum {getattr(self, 'max_agents', 50)}")

        # Initialize other attributes
        self.project_path = Path(self.path).expanduser().resolve()
        self.combined_file = self.project_path / "combined_typechecker_and_linter_problems.txt"
        self.prompt_text = self._load_prompt()
        self.monitor: Optional[AgentMonitor] = None
        self.running = True
        self.shutting_down = False

        # Git settings from config
        self.git_branch: Optional[str] = getattr(self, "git_branch", None)
        self.git_remote: str = getattr(self, "git_remote", "origin")
        self._cleanup_registered = False
        self.state_file = self.project_path / MONITOR_STATE_FILE
        
        # Signal handling for double Ctrl-C
        self._last_sigint_time: Optional[float] = None
        self._force_kill_threshold = 3.0  # seconds

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self, config_path: str) -> None:
        """Load settings from JSON config file"""
        config_file = Path(config_path)
        if config_file.exists():
            with config_file.open() as f:
                config_data = json.load(f)
                # Accept all config values, not just existing attributes
                for key, value in config_data.items():
                    setattr(self, key, value)

    def _signal_handler(self, sig: Any, frame: Any) -> None:
        """Handle shutdown signals gracefully with force-kill on double tap"""
        current_time = time.time()
        
        # Check if this is a SIGINT (Ctrl-C)
        if sig == signal.SIGINT:
            # Check for double tap
            if self._last_sigint_time and (current_time - self._last_sigint_time) < self._force_kill_threshold:
                # Second Ctrl-C within threshold - force kill
                console.print("\n[red]Force killing tmux session...[/red]")
                with contextlib.suppress(Exception):
                    run(f"tmux kill-session -t {self.session}", check=False, quiet=True)
                # Clean up state files
                try:
                    if hasattr(self, "state_file") and self.state_file.exists():
                        self.state_file.unlink()
                    lock_file = Path.home() / ".claude" / ".agent_farm_launch.lock"
                    if lock_file.exists():
                        lock_file.unlink()
                except Exception:
                    pass
                # Force exit
                os._exit(1)
            else:
                # First Ctrl-C or outside threshold
                self._last_sigint_time = current_time
                if not self.shutting_down:
                    self.shutting_down = True
                    console.print("\n[yellow]Received interrupt signal. Shutting down gracefully...[/yellow]")
                    console.print("[dim]Press Ctrl-C again within 3 seconds to force kill[/dim]")
                    self.running = False
        else:
            # Other signals (SIGTERM, etc.) - normal graceful shutdown
            if not self.shutting_down:
                self.shutting_down = True
                console.print("\n[yellow]Received termination signal. Shutting down gracefully...[/yellow]")
                self.running = False

    def _backup_claude_settings(self) -> Optional[str]:
        """Backup essential Claude Code settings (excluding large caches)"""
        claude_dir = Path.home() / ".claude"
        if not claude_dir.exists():
            console.print("[yellow]No Claude Code directory found to backup[/yellow]")
            return None
        
        try:
            # Create backup directory in project
            backup_dir = self.project_path / ".claude_agent_farm_backups"
            backup_dir.mkdir(exist_ok=True)
            
            # Create timestamped backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_type = "full" if self.full_backup else "essential"
            backup_file = backup_dir / f"claude_backup_{backup_type}_{timestamp}.tar.gz"
            
            # Create compressed backup
            import tarfile
            
            if self.full_backup:
                console.print("[dim]Creating FULL backup of ~/.claude directory (this may take a while)...[/dim]")
                
                with tarfile.open(backup_file, "w:gz") as tar:
                    # Use filter to preserve all metadata
                    def reset_ids(tarinfo):
                        # Preserve all metadata but reset user/group to current user
                        # This prevents permission issues on restore
                        tarinfo.uid = os.getuid()
                        tarinfo.gid = os.getgid()
                        return tarinfo
                    
                    tar.add(claude_dir, arcname="claude", filter=reset_ids)
                
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                console.print(f"[green]✓ Full backup completed: {backup_file.name} ({size_mb:.1f} MB)[/green]")
            else:
                console.print("[dim]Creating backup of essential Claude settings...[/dim]")
                
                with tarfile.open(backup_file, "w:gz") as tar:
                    # Filter to preserve metadata
                    def reset_ids(tarinfo):
                        tarinfo.uid = os.getuid()
                        tarinfo.gid = os.getgid()
                        return tarinfo
                    
                    # Add settings.json if it exists
                    settings_file = claude_dir / "settings.json"
                    if settings_file.exists():
                        tar.add(settings_file, arcname="claude/settings.json", filter=reset_ids)
                    
                    # Add ide directory (usually empty or small)
                    ide_dir = claude_dir / "ide"
                    if ide_dir.exists():
                        tar.add(ide_dir, arcname="claude/ide", filter=reset_ids)
                    
                    # Add statsig directory (small, contains feature flags)
                    statsig_dir = claude_dir / "statsig"
                    if statsig_dir.exists():
                        tar.add(statsig_dir, arcname="claude/statsig", filter=reset_ids)
                    
                    # Optionally add todos (usually small)
                    todos_dir = claude_dir / "todos"
                    if todos_dir.exists():
                        # Check size first
                        todos_size = sum(f.stat().st_size for f in todos_dir.rglob("*") if f.is_file())
                        if todos_size < 10 * 1024 * 1024:  # Less than 10MB
                            tar.add(todos_dir, arcname="claude/todos", filter=reset_ids)
                        else:
                            console.print(f"[dim]Skipping todos directory ({todos_size / 1024 / 1024:.1f} MB)[/dim]")
                    
                    # Skip projects directory - it's just caches
                    console.print("[dim]Skipping projects/ directory (caches)[/dim]")
                
                # Get backup size
                size_kb = backup_file.stat().st_size / 1024
                console.print(f"[green]✓ Backed up Claude settings to {backup_file.name} ({size_kb:.1f} KB)[/green]")
            
            # Clean up old backups (keep last 10)
            self._cleanup_old_backups(backup_dir, keep_count=10)
            
            return str(backup_file)
        except Exception as e:
            console.print(f"[red]Error: Could not backup Claude directory: {e}[/red]")
            return None

    def _cleanup_old_backups(self, backup_dir: Path, keep_count: int = 10, max_total_mb: int = 200) -> None:
        """Remove old backups, keeping only the most recent ones and enforcing size limit"""
        try:
            # Find all backup files (both essential and full)
            backups = sorted(backup_dir.glob("claude_backup_*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Calculate total size and remove old backups based on both count and size limits
            total_size_bytes = 0
            max_size_bytes = max_total_mb * 1024 * 1024
            
            backups_to_keep = []
            backups_to_remove = []
            
            for i, backup in enumerate(backups):
                backup_size = backup.stat().st_size
                
                # Keep backup if we're under both the count limit and size limit
                if i < keep_count and total_size_bytes + backup_size <= max_size_bytes:
                    total_size_bytes += backup_size
                    backups_to_keep.append(backup)
                else:
                    backups_to_remove.append(backup)
            
            # Always keep at least the most recent backup
            if not backups_to_keep and backups:
                backups_to_keep.append(backups[0])
                backups_to_remove = backups[1:]
            
            # Remove old backups
            for old_backup in backups_to_remove:
                size_mb = old_backup.stat().st_size / (1024 * 1024)
                old_backup.unlink()
                console.print(f"[dim]Removed old backup: {old_backup.name} ({size_mb:.1f} MB)[/dim]")
            
            # Report current backup storage status
            if backups_to_keep:
                total_mb = total_size_bytes / (1024 * 1024)
                console.print(f"[dim]Backup storage: {len(backups_to_keep)} files, {total_mb:.1f} MB total[/dim]")
                
        except Exception as e:
            console.print(f"[yellow]Warning: Could not clean up old backups: {e}[/yellow]")

    def _restore_claude_settings(self, backup_path: Optional[str] = None) -> bool:
        """Restore Claude Code settings from backup"""
        try:
            # If no backup path provided, use the most recent one
            if backup_path is None:
                backup_path = self.settings_backup_path
            
            if not backup_path:
                console.print("[red]No backup path available[/red]")
                return False
            
            backup_file = Path(backup_path)
            if not backup_file.exists():
                console.print(f"[red]Backup file not found: {backup_path}[/red]")
                return False
            
            claude_dir = Path.home() / ".claude"
            
            # For partial backups, we don't need to remove the entire directory
            # Just extract over existing files
            try:
                # Ensure claude directory exists
                claude_dir.mkdir(exist_ok=True)
                
                # Save original metadata of existing files
                existing_metadata = {}
                for item in claude_dir.rglob("*"):
                    if item.exists():
                        stat = item.stat()
                        existing_metadata[str(item)] = {
                            'mode': stat.st_mode,
                            'mtime': stat.st_mtime,
                            'atime': stat.st_atime,
                        }
                
                # Extract backup
                import tarfile
                console.print(f"[dim]Restoring from {backup_file.name}...[/dim]")
                
                with tarfile.open(backup_file, "r:gz") as tar:
                    # Extract with numeric owner to preserve permissions
                    tar.extractall(path=claude_dir.parent, numeric_owner=True)
                    
                    # Get list of extracted files to preserve their times
                    for member in tar.getmembers():
                        if member.isfile():
                            extracted_path = claude_dir.parent / member.name
                            if extracted_path.exists():
                                # Preserve the modification time from the archive
                                os.utime(extracted_path, (member.mtime, member.mtime))
                
                # Ensure proper permissions on sensitive files
                settings_file = claude_dir / "settings.json"
                if settings_file.exists():
                    # Ensure settings.json has appropriate permissions (readable by user only)
                    os.chmod(settings_file, 0o600)
                
                # Set ownership to current user for all restored files
                uid = os.getuid()
                gid = os.getgid()
                
                for root, dirs, files in os.walk(claude_dir):
                    for d in dirs:
                        path = Path(root) / d
                        with contextlib.suppress(Exception):
                            os.chown(path, uid, gid)
                    for f in files:
                        path = Path(root) / f
                        with contextlib.suppress(Exception):
                            os.chown(path, uid, gid)
                
                console.print("[green]✓ Restored Claude settings from backup[/green]")
                
                # Check and fix permissions after restore
                self._check_claude_permissions()
                
                return True
                
            except Exception as e:
                console.print(f"[red]Error during restore: {e}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]Error restoring Claude settings: {e}[/red]")
            return False

    def _copy_best_practices_guides(self) -> None:
        """Copy best practices guides to the project folder if configured"""
        best_practices_files = getattr(self, 'best_practices_files', [])
        if not best_practices_files:
            return
            
        # Ensure it's a list
        if isinstance(best_practices_files, str):
            best_practices_files = [best_practices_files]
            
        # Copy to project's best_practices_guides folder
        dest_dir = self.project_path / "best_practices_guides"
        dest_dir.mkdir(exist_ok=True)
        
        # Copy specified files
        copied_files = []
        for file_path in best_practices_files:
            source_file = Path(file_path).expanduser().resolve()
            if not source_file.exists():
                console.print(f"[yellow]Best practices file not found: {source_file}[/yellow]")
                continue
                
            dest_file = dest_dir / source_file.name
            try:
                import shutil
                shutil.copy2(source_file, dest_file)
                copied_files.append(source_file.name)
            except Exception as e:
                console.print(f"[yellow]Failed to copy {source_file.name}: {e}[/yellow]")
        
        if copied_files:
            console.print(f"[green]✓ Copied {len(copied_files)} best practices guide(s) to project[/green]")
            for filename in copied_files:
                console.print(f"  - {filename}")

    def _load_prompt(self) -> str:
        """Load prompt from file and substitute variables"""
        if self.prompt_file:
            prompt_path = Path(self.prompt_file)
            if not prompt_path.exists():
                console.print(f"[red]Error: Prompt file not found: {self.prompt_file}[/red]")
                raise ValueError(f"Prompt file not found: {self.prompt_file}")
            prompt_text = prompt_path.read_text().strip()
            if not prompt_text:
                raise ValueError(f"Prompt file is empty: {self.prompt_file}")
        else:
            # Try to find a default prompt file
            default_prompts = [
                self.project_path / "prompts" / f"default_prompt_{getattr(self, 'tech_stack', 'nextjs')}.txt",
                self.project_path / "prompts" / "default_prompt.txt",
                Path(__file__).parent / "prompts" / f"default_prompt_{getattr(self, 'tech_stack', 'nextjs')}.txt",
                Path(__file__).parent / "prompts" / "default_prompt.txt",
            ]
            
            prompt_text = None
            for prompt_path in default_prompts:
                if prompt_path.exists():
                    prompt_text = prompt_path.read_text().strip()
                    break
            
            if not prompt_text:
                raise ValueError("No prompt file specified and no default prompt found. Use --prompt-file to specify a prompt.")
        
        # Substitute variables in the prompt
        chunk_size = getattr(self, 'chunk_size', 50)
        prompt_text = prompt_text.replace('{chunk_size}', str(chunk_size))
        
        # Future: could add more substitutions here
        # prompt_text = prompt_text.replace('{tech_stack}', getattr(self, 'tech_stack', 'generic'))
        
        return prompt_text
    
    def _calculate_dynamic_chunk_size(self) -> int:
        """Calculate optimal chunk size based on remaining lines in the problems file"""
        if not self.combined_file.exists():
            return getattr(self, 'chunk_size', 50)
        
        # Count total lines in problems file
        total_lines = line_count(self.combined_file)
        
        # If file is small or empty, use minimum chunk size
        if total_lines < 100:
            return 10
        
        # Calculate optimal chunk size: max(10, total_lines / agents / 2)
        # This ensures agents have work but not too much per iteration
        optimal_chunk = max(10, total_lines // self.agents // 2)
        
        # Cap at configured maximum if specified
        configured_chunk = getattr(self, 'chunk_size', 50)
        return min(optimal_chunk, configured_chunk)

    def regenerate_problems(self) -> None:
        """Regenerate the type-checker and linter problems file"""
        if self.skip_regenerate:
            console.print("[yellow]Skipping problem file regeneration[/yellow]")
            return

        console.rule("[yellow]Regenerating type-check and lint output")

        # Get commands from config or use defaults based on tech stack
        tech_stack = getattr(self, 'tech_stack', 'nextjs')
        
        # Default commands for different tech stacks
        default_commands = {
            'nextjs': {
                'type_check': ["bun", "run", "type-check"],
                'lint': ["bun", "run", "lint"]
            },
            'python': {
                'type_check': ["mypy", "."],
                'lint': ["ruff", "check", "."]
            }
        }
        
        # Use configured commands or fall back to defaults
        commands = getattr(self, 'problem_commands', default_commands.get(tech_stack, default_commands['nextjs']))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Running type-check and lint...", total=None)

            os.chdir(self.project_path)

            # Use a proper temporary file to avoid conflicts
            tmpfile_fd, tmpfile_name = tempfile.mkstemp(
                dir=self.project_path, prefix="combined_", suffix=".tmp", text=True
            )
            tmpfile_path = Path(tmpfile_name)
            
            try:
                with os.fdopen(tmpfile_fd, 'w') as tmpfile:
                    # Run type-check
                    type_check_cmd = commands.get('type_check')
                    if type_check_cmd:
                        tmpfile.write(f"$ {' '.join(type_check_cmd)}\n")
                        tmpfile.flush()

                        # Check if we should continue
                        if not self.running:
                            raise KeyboardInterrupt()

                        result = subprocess.run(
                            type_check_cmd, stdout=tmpfile, stderr=subprocess.STDOUT, cwd=self.project_path
                        )
                        # Ensure all output is written to disk
                        tmpfile.flush()
                        os.fsync(tmpfile.fileno())
                        
                        # Small delay to ensure process cleanup
                        time.sleep(0.5)

                    # Run lint
                    lint_cmd = commands.get('lint')
                    if lint_cmd:
                        if type_check_cmd:  # Add spacing if we ran type-check
                            tmpfile.write("\n\n")
                        tmpfile.write(f"$ {' '.join(lint_cmd)}\n")
                        tmpfile.flush()

                        # Check again before lint
                        if not self.running:
                            raise KeyboardInterrupt()

                        result = subprocess.run(lint_cmd, stdout=tmpfile, stderr=subprocess.STDOUT, cwd=self.project_path)  # noqa: F841
                        # Ensure all output is written to disk
                        tmpfile.flush()
                        os.fsync(tmpfile.fileno())
                
                # File is now closed, safe to move
                # Atomic rename (handle cross-filesystem moves)
                try:
                    tmpfile_path.replace(self.combined_file)
                except OSError:
                    # Fallback for cross-filesystem scenarios
                    import shutil

                    shutil.move(str(tmpfile_path), str(self.combined_file))
            except (KeyboardInterrupt, Exception):
                # Clean up temp file on any error
                tmpfile_path.unlink(missing_ok=True)
                raise

            progress.update(task, completed=True)

        # Count problems before and after
        prev_count = getattr(self, '_last_problem_count', 0)
        count = line_count(self.combined_file)
        console.print(f"[green]✓ Generated {count} lines of problems[/green]")
        
        # Track problems fixed (decrease in count)
        if prev_count > 0 and count < prev_count:
            problems_fixed = prev_count - count
            self.total_problems_fixed += problems_fixed
            console.print(f"[green]✓ Fixed {problems_fixed} problems this cycle[/green]")
        
        # Store current count for next comparison
        self._last_problem_count = count

    def commit_and_push(self) -> None:
        """Commit and push the updated problem count"""
        if self.skip_commit:
            console.print("[yellow]Skipping git commit/push[/yellow]")
            return

        console.rule("[yellow]Committing updated problem count")

        # Verify we're in a git repository
        ret, _, _ = run("git rev-parse --is-inside-work-tree", capture=True, quiet=True, check=False)
        if ret != 0:
            console.print("[red]Error: Not in a git repository[/red]")
            console.print("[yellow]Skipping git operations[/yellow]")
            return

        # Check for uncommitted changes
        # First, check if the problems file exists and has changes
        if self.combined_file.exists():
            ret, stdout, _ = run(
                f"git diff --name-only {shlex.quote(str(self.combined_file))}", capture=True, quiet=True
            )
            if stdout.strip():
                console.print(
                    f"[yellow]Warning: {self.combined_file.name} has uncommitted changes that will be committed[/yellow]"
                )

        ret, stdout, _ = run("git status --porcelain", capture=True, quiet=True)
        if stdout.strip():
            console.print("[yellow]You have uncommitted changes:[/yellow]")
            console.print(stdout)
            console.print("[yellow]The agent farm will add and commit the problems file.[/yellow]")
            console.print("[yellow]Other uncommitted changes will remain uncommitted.[/yellow]")
            if not interruptible_confirm("Do you want to continue?"):
                raise typer.Exit(1)

        # Ensure we're on a branch (not detached HEAD)
        ret, stdout, _ = run("git symbolic-ref HEAD", capture=True, quiet=True, check=False)
        if ret != 0:
            console.print("[red]Error: You're in a detached HEAD state[/red]")
            console.print("[yellow]Please checkout a branch before running the agent farm[/yellow]")
            raise typer.Exit(1)

        count = line_count(self.combined_file)

        try:
            run(f"git add {shlex.quote(str(self.combined_file))}")

            # Capture commit output to check if anything was actually committed
            commit_cmd = ["git", "commit", "-m", f"Before next round of fixes; currently {count} lines of problems"]
            commit_result = subprocess.run(commit_cmd, capture_output=True, text=True)

            both = (commit_result.stdout or "") + (commit_result.stderr or "")
            if commit_result.returncode != 0:  # noqa: SIM102
                if "nothing to commit" in both or "no changes added" in both:
                    console.print("[yellow]No changes to commit - skipping push[/yellow]")
                    return
                # Other errors still show warning below

            # Determine branch and remote
            branch = self.git_branch
            if not branch:
                _, stdout, _ = run("git rev-parse --abbrev-ref HEAD", capture=True, quiet=True)
                branch = stdout.strip() or "HEAD"

            remote = self.git_remote
            run(f"git push {remote} {branch}", check=False)
            console.print(f"[green]✓ Pushed commit with {count} current problems[/green]")
            
            # Track commit for reporting
            self.total_commits_made += 1
            
            # Display rich diff summary
            self._display_commit_diff()
        except subprocess.CalledProcessError:
            console.print("[yellow]⚠ git commit/push skipped (no changes?)")

    def _display_commit_diff(self) -> None:
        """Display a rich diff summary of the last commit"""
        try:
            # Get diff stats for the last commit
            _, stdout, _ = run("git diff --stat HEAD~1..HEAD", capture=True, quiet=True)
            if not stdout.strip():
                return
            
            # Create a rich panel with the diff information
            console.print()  # Add space before
            console.print(Panel(
                stdout.strip(),
                title="[bold cyan]📊 Commit Diff Summary[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED
            ))
            
            # Get short summary of changes
            _, stdout, _ = run("git diff --shortstat HEAD~1..HEAD", capture=True, quiet=True)
            if stdout.strip():
                console.print(f"[dim]{stdout.strip()}[/dim]")
            
            # Get list of changed files
            _, stdout, _ = run("git diff --name-status HEAD~1..HEAD", capture=True, quiet=True)
            if stdout.strip():
                lines = stdout.strip().split('\n')
                modified_count = sum(1 for line in lines if line.startswith('M'))
                added_count = sum(1 for line in lines if line.startswith('A'))
                deleted_count = sum(1 for line in lines if line.startswith('D'))
                
                summary_parts = []
                if modified_count > 0:
                    summary_parts.append(f"[yellow]{modified_count} modified[/yellow]")
                if added_count > 0:
                    summary_parts.append(f"[green]{added_count} added[/green]")
                if deleted_count > 0:
                    summary_parts.append(f"[red]{deleted_count} deleted[/red]")
                
                if summary_parts:
                    console.print(f"Files: {', '.join(summary_parts)}")
            
            console.print()  # Add space after
            
        except Exception as e:
            # Don't fail the whole operation if diff display fails
            console.print(f"[dim]Could not display diff summary: {e}[/dim]")

    def _wait_for_shell_prompt(self, pane_target: str, timeout: int = 30, ignore_shutdown: bool = False) -> bool:
        """Wait for a shell prompt to appear in the pane
        
        Args:
            pane_target: The tmux pane to check
            timeout: Maximum time to wait in seconds
            ignore_shutdown: If True, don't abort on shutdown signal (for error recovery)
        """
        start_time = time.time()
        content: str = ""  # prevents UnboundLocalError on early exit
        last_content = ""
        debug_shown = False

        # ------------------------- Active probe setup ------------------------- #
        # Some shell configurations use very minimal or custom prompts that the
        # passive heuristics below cannot reliably detect.  To accommodate a
        # wider variety of prompts we fall back to sending an `echo` command
        # containing a unique marker and waiting for that marker to appear in
        # the captured pane output.  These variables keep track of the probe
        # state for the duration of the wait loop.
        probe_attempted = False  # Whether we've sent the probe command yet
        probe_marker: str = ""   # The unique string we expect to see echoed back

        # Get the last part of the project path for detection
        project_dir_name = self.project_path.name

        while time.time() - start_time < timeout and (ignore_shutdown or self.running):
            content = tmux_capture(pane_target)
            if content and content != last_content:
                lines = content.strip().splitlines()
                if lines:
                    # Only show debug output once per pane
                    if not debug_shown and len(lines[-1]) > 0:
                        console.print(f"[dim]Pane {pane_target}: ...{lines[-1][-50:]}[/dim]")
                        debug_shown = True

                    # Skip if direnv is still loading
                    if any("direnv:" in line for line in lines[-3:]):
                        continue  # Wait for direnv to finish

                    # Check if we see the project directory in the prompt
                    # This works with most modern shells that show the current directory
                    # Look through ALL lines, not just the last few, since prompts can be complex
                    for line in lines:
                        if project_dir_name in line:
                            console.print(f"[dim]Found project directory '{project_dir_name}' in prompt[/dim]")
                            return True

                    # Fall back to traditional prompt detection
                    # Look for common shell prompt patterns at the end of the last line
                    if re.search(r"[\$%>#]\s*$", lines[-1]):
                        return True
                    # Also check for other common prompt patterns
                    if re.search(r"❯\s*$", lines[-1]):  # Starship/PowerLevel10k style  # noqa: RUF001
                        return True
                    if re.search(r"➜\s*$", lines[-1]):  # Oh-my-zsh default
                        return True
                    if re.search(r"\]\s*$", lines[-1]) and "[" in lines[-1]:  # Bracketed prompts
                        return True
                    # Check for git prompt patterns like "on main"
                    if re.search(r"on\s+\S+.*\s*$", lines[-1]):  # Git branch info
                        console.print("[dim]Detected git prompt pattern[/dim]")
                        return True
                last_content = content

            # ------------------------------------------------------------------ #
            # Active probe logic - short-circuit the function as soon as we see
            # the unique probe marker in the pane output, which demonstrates
            # that the shell is accepting and executing commands.
            # ------------------------------------------------------------------ #
            elapsed = time.time() - start_time

            # 1) If we already sent a probe and the marker appears → ready.
            if probe_attempted and probe_marker and probe_marker in content:
                console.print(f"[dim]Pane {pane_target}: Shell responded to probe - ready[/dim]")
                # Clear the temporary probe output so it does not clutter the pane
                tmux_send(pane_target, "clear", enter=True, update_heartbeat=False)
                return True

            # 2) If passive detection has not succeeded within ~3 s, send probe.
            if (not probe_attempted) and (elapsed > 3):
                probe_attempted = True
                from random import randint  # local import to avoid top-of-file churn
                probe_marker = f"AGENT_FARM_READY_{randint(100000, 999999)}"
                tmux_send(pane_target, f"echo {probe_marker}", enter=True, update_heartbeat=False)
                # Give the shell a brief moment to execute the probe before we
                # capture output again in the next loop iteration.
                time.sleep(0.2)
                continue  # Skip the remainder of this iteration

            time.sleep(0.2)

        # Check if we were interrupted
        if not self.running:
            console.print("[yellow]Shell prompt check interrupted by shutdown signal[/yellow]")
            return False

        # Show final content if we timeout
        if content:
            lines = content.strip().splitlines()
            if lines:
                console.print(f"[yellow]Timeout waiting for prompt in {pane_target}[/yellow]")
                console.print(f"[yellow]Last line: {lines[-1]}[/yellow]")
                # Show more context to help debug
                if len(lines) > 1:
                    console.print("[dim]Previous lines:[/dim]")
                    for line in lines[-5:-1]:  # Show up to 4 lines before the last
                        console.print(f"[dim]  {line}[/dim]")
        else:
            console.print(f"[yellow]Timeout waiting for prompt in {pane_target}. No content captured.[/yellow]")

        return False

    def setup_tmux_session(self) -> None:
        """Create tmux session with tiled agent panes"""
        console.rule(f"[yellow]Creating tmux session '{self.session}' with {self.agents} agents")

        # Kill existing session if it exists
        run(f"tmux kill-session -t {self.session}", check=False, quiet=True)
        time.sleep(0.5)

        # Create new session with controller window
        run(f"tmux new-session -d -s {self.session} -n controller")
        # CRITICAL: Set POWERLEVEL9K_INSTANT_PROMPT=off for ALL panes including the first one
        run(f"tmux new-window -t {self.session} -n agents -e 'POWERLEVEL9K_INSTANT_PROMPT=off'", quiet=True)

        # Create agent panes in tiled layout
        for i in range(self.agents):
            if i > 0:
                # CRITICAL: Set POWERLEVEL9K_INSTANT_PROMPT=off when creating the pane
                # This ensures it's disabled BEFORE the shell initializes
                run(f"tmux split-window -t {self.session}:agents -e 'POWERLEVEL9K_INSTANT_PROMPT=off'", quiet=True)
                run(f"tmux select-layout -t {self.session}:agents tiled", quiet=True)

        # Get the actual pane IDs - retry until we have the right count
        console.print("[dim]Waiting for tmux panes to be created...[/dim]")
        pane_ids = []
        start_time = time.time()
        timeout = 10  # 10 seconds max to create panes

        while time.time() - start_time < timeout:
            _, pane_list, _ = run(
                f"tmux list-panes -t {self.session}:agents -F '#{{pane_index}}'", capture=True, quiet=True
            )
            pane_ids = sorted(  # make mapping deterministic
                (pid.strip() for pid in pane_list.strip().splitlines() if pid.strip()),
                key=int,
            )

            if len(pane_ids) == self.agents:
                break

            time.sleep(0.1)

        # Create mapping from agent ID to actual pane ID
        if len(pane_ids) != self.agents:
            console.print(f"[red]Error: Expected {self.agents} panes but found {len(pane_ids)}[/red]")
            console.print(f"[red]Pane IDs found: {pane_ids}[/red]")
            raise RuntimeError("Failed to create the expected number of tmux panes")

        for agent_id, pane_id in enumerate(pane_ids[: self.agents]):
            self.pane_mapping[agent_id] = f"{self.session}:agents.{pane_id}"

        # Wait for all panes to have shell prompts ready
        if not self.fast_start:
            console.print("[dim]Waiting for shell prompts in all panes...[/dim]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                transient=True,
            ) as progress:
                task = progress.add_task("Initializing panes", total=self.agents)

                for agent_id, pane_target in self.pane_mapping.items():
                    if not self.running:
                        console.print("[yellow]Initialization interrupted by shutdown signal[/yellow]")
                        raise KeyboardInterrupt()

                    if self._wait_for_shell_prompt(pane_target):
                        progress.update(task, advance=1)
                    else:
                        console.print(f"[yellow]Warning: Pane {agent_id} slow to initialize[/yellow]")
                        progress.update(task, advance=1)
        else:
            console.print("[dim]Fast start enabled - skipping shell prompt checks[/dim]")
            # Just wait a moment for panes to settle
            time.sleep(1.0)

        # Enable mouse support if configured
        if self.tmux_mouse:
            run(f"tmux set-option -t {self.session} -g mouse on", quiet=True)
        
        # Enable pane titles for context display
        run(f"tmux set-option -t {self.session} -g pane-border-status top", quiet=True)
        run(f"tmux set-option -t {self.session} -g pane-border-format ' #{{pane_title}} '", quiet=True)

        # Automatically adjust font size for many panes
        if self.agents >= 10:
            console.print(f"[yellow]Optimizing display for {self.agents} panes...[/yellow]")

            # Calculate zoom level needed
            zoom_steps = 3 if self.agents >= 20 else 2 if self.agents >= 15 else 1

            # If we're already in tmux, we can control the client zoom
            if os.environ.get("TMUX"):
                # We're in tmux - use client commands
                for _ in range(zoom_steps):
                    run("tmux resize-pane -Z", quiet=True, check=False)  # Toggle zoom
                    run("tmux send-keys C--", quiet=True, check=False)  # Send Ctrl+-
                    time.sleep(0.05)
            else:
                # Try to auto-zoom using escape sequences (works in some terminals)
                # This will be ignored by terminals that don't support it
                if sys.platform == "darwin":  # macOS
                    # iTerm2 specific
                    sys.stdout.write(f"\033]1337;SetProfile=FontSize={(14 - zoom_steps)}\007")
                else:
                    # Generic terminals - try zoom out escape sequence
                    for _ in range(zoom_steps):
                        sys.stdout.write("\033[1;2'-'")  # Some terminals recognize this
                sys.stdout.flush()

            # Optimize tmux display
            run(f"tmux set-option -t {self.session} -g pane-border-style 'fg=colour240,bg=colour235'", quiet=True)
            run(
                f"tmux set-option -t {self.session} -g pane-active-border-style 'fg=colour250,bg=colour235'", quiet=True
            )
            run(f"tmux set-option -t {self.session} -g pane-border-lines single", quiet=True)
            run(f"tmux set-option -t {self.session} -g pane-border-status off", quiet=True)

            # Hide status bar to save space
            run(f"tmux set-option -t {self.session} -g status off", quiet=True)

            # Set aggressive resize for better space usage
            run(f"tmux set-option -t {self.session} -g aggressive-resize on", quiet=True)

            # If zoom didn't work automatically, remind user
            console.print("[dim]If text is too large, zoom out with: Ctrl/Cmd + minus (-)[/dim]")
            console.print(f"[dim]Zoom level suggested: {zoom_steps} step{'s' if zoom_steps > 1 else ''}[/dim]")

            self._zoom_adjusted = True

        # Launch monitor in controller window if monitoring is enabled
        if not self.no_monitor:
            # Get the current script path
            script_path = Path(__file__).resolve()
            # Launch monitor mode in controller pane
            monitor_cmd = f"cd {self.project_path} && {sys.executable} {script_path} monitor-only --path {self.project_path} --session {self.session}"
            tmux_send(f"{self.session}:controller", monitor_cmd)

        # Set up context-reset macro binding
        # Bind Ctrl+r in the controller window to send /clear to all agent panes
        reset_cmd = ""
        for agent_id in range(self.agents):
            target_pane = self.pane_mapping.get(agent_id)
            if target_pane is not None:
                # Send /clear to each agent pane
                reset_cmd += f"send-keys -t {target_pane} '/clear' Enter \\; "
        
        if reset_cmd:
            # Remove the trailing " \; "
            reset_cmd = reset_cmd[:-4]
            # Bind to Ctrl+r in the controller window
            run(f"tmux bind-key -T root -n C-r \\; display-message 'Sending /clear to all agents...' \\; {reset_cmd}", quiet=True)
            console.print("[green]✓ Context-reset macro bound to Ctrl+R (broadcasts /clear to all agents)[/green]")

        # Register cleanup handler
        if not self._cleanup_registered:
            import atexit

            atexit.register(self._emergency_cleanup)
            self._cleanup_registered = True

        console.print(f"[green]✓ Created session with {self.agents} panes[/green]")

    def _acquire_claude_lock(self, timeout: float = 5.0) -> bool:
        """Acquire a lock file to prevent concurrent Claude Code launches"""
        lock_file = Path.home() / ".claude" / ".agent_farm_launch.lock"
        lock_file.parent.mkdir(exist_ok=True)

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try to create lock file exclusively
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()}\n".encode())
                os.close(fd)
                return True
            except FileExistsError:
                # Lock file exists, check if it's stale
                try:
                    if lock_file.exists():  # noqa: SIM102
                        # Check if lock is older than 30 seconds (likely stale)
                        if time.time() - lock_file.stat().st_mtime > 30:
                            lock_file.unlink()
                            continue
                except Exception:
                    pass
                time.sleep(0.1)

        return False

    def _release_claude_lock(self) -> None:
        """Release the Claude Code launch lock"""
        lock_file = Path.home() / ".claude" / ".agent_farm_launch.lock"
        with contextlib.suppress(Exception):
            lock_file.unlink()

    def _check_claude_permissions(self) -> bool:
        """Check and fix permissions on Claude settings files"""
        claude_dir = Path.home() / ".claude"
        settings_file = claude_dir / "settings.json"
        
        try:
            if settings_file.exists():
                # Get current permissions
                current_mode = settings_file.stat().st_mode & 0o777
                
                # Check if permissions are too open
                if current_mode != 0o600:
                    console.print(f"[yellow]Fixing permissions on {settings_file.name} (was {oct(current_mode)})[/yellow]")
                    os.chmod(settings_file, 0o600)
                
                # Ensure we own the file
                stat_info = settings_file.stat()
                if stat_info.st_uid != os.getuid():
                    console.print(f"[yellow]Fixing ownership on {settings_file.name}[/yellow]")
                    try:
                        os.chown(settings_file, os.getuid(), os.getgid())
                    except PermissionError:
                        console.print("[red]Could not change ownership - may need sudo[/red]")
                        return False
            
            # Check directory permissions
            if claude_dir.exists():
                dir_mode = claude_dir.stat().st_mode & 0o777
                if dir_mode not in (0o700, 0o755):
                    console.print(f"[yellow]Fixing permissions on .claude directory (was {oct(dir_mode)})[/yellow]")
                    os.chmod(claude_dir, 0o700)
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error checking permissions: {e}[/red]")
            return False

    def start_agent(self, agent_id: int, restart: bool = False) -> None:
        """Start or restart a single agent"""
        pane_target = self.pane_mapping.get(agent_id)
        if not pane_target:
            console.print(f"[red]Error: No pane mapping found for agent {agent_id}[/red]")
            return

        if restart:
            # Exit current session
            tmux_send(pane_target, "/exit")
            # Wait for shell prompt to appear
            if not self._wait_for_shell_prompt(pane_target, timeout=15):
                console.print(f"[yellow]Warning: Agent {agent_id} pane slow to return to shell prompt[/yellow]")

            if self.monitor:
                self.monitor.agents[agent_id]["cycles"] += 1

        # Navigate and start Claude Code
        # Quote the path so directories with spaces or shell metacharacters work
        tmux_send(pane_target, f"cd {shlex.quote(str(self.project_path))}")
        
        # CRITICAL: Wait a couple seconds for cd to complete and shell to stabilize
        # This prevents race conditions and ensures we're in the right directory
        console.print(f"[dim]Agent {agent_id:02d}: Waiting 2s after cd before launching cc...[/dim]")
        time.sleep(2.0)

        # Acquire lock before launching cc to prevent config corruption
        lock_acquired = False
        if not self._acquire_claude_lock(timeout=10.0):
            console.print(f"[yellow]Agent {agent_id:02d}: Waiting for lock to launch cc...[/yellow]")
            # Try once more with longer timeout
            if not self._acquire_claude_lock(timeout=20.0):
                console.print(f"[red]Agent {agent_id:02d}: Could not acquire lock - aborting launch[/red]")
                if self.monitor:
                    self.monitor.agents[agent_id]["status"] = "error"
                    self.monitor.agents[agent_id]["errors"] += 1
                return

        lock_acquired = True
        try:
            tmux_send(pane_target, "cc")

            if not restart:
                console.print(f"🛠  Agent {agent_id:02d}: launching cc, waiting {self.wait_after_cc}s...")

            # Make wait_after_cc interruptible
            for _ in range(int(self.wait_after_cc * 5)):
                if not self.running:
                    return
                time.sleep(0.2)
        finally:
            # Always release lock
            if lock_acquired:
                self._release_claude_lock()

        # Verify Claude Code started successfully
        max_retries = 5
        claude_started_successfully = False

        # Give Claude Code a bit more time to fully initialize before first check
        time.sleep(2.0)

        for attempt in range(max_retries):
            if not self.running:
                return

            content = tmux_capture(pane_target)

            # Debug log for troubleshooting startup detection
            if attempt == 0 and len(content.strip()) > 0:
                console.print(f"[dim]Agent {agent_id:02d}: Captured {len(content)} chars, checking readiness...[/dim]")
                # Log key indicators for debugging
                if "Welcome to Claude Code!" in content:
                    console.print(f"[dim]Agent {agent_id:02d}: Found welcome message[/dim]")
                if "│ >" in content:
                    console.print(f"[dim]Agent {agent_id:02d}: Found prompt box[/dim]")
                if "? for shortcuts" in content:
                    console.print(f"[dim]Agent {agent_id:02d}: Found shortcuts hint[/dim]")

            # Check for various failure conditions
            if not content or len(content.strip()) < 10:
                # Empty or nearly empty content indicates cc didn't start
                console.print(
                    f"[yellow]Agent {agent_id:02d}: No output from Claude Code yet (attempt {attempt + 1}/{max_retries})[/yellow]"
                )
            elif self.monitor and self.monitor.is_claude_ready(content):
                # Check for readiness FIRST before checking for errors
                claude_started_successfully = True
                break
            elif self.monitor and len(content.strip()) > 100 and (
                self.monitor.has_settings_error(content) or self.monitor.has_welcome_screen(content)
            ):
                # Only check for errors if we have substantial content (>100 chars)
                console.print(
                    f"[red]Agent {agent_id:02d}: Settings error/setup screen detected - attempting restore[/red]"
                )

                # Kill this cc instance more forcefully
                console.print(f"[yellow]Agent {agent_id:02d}: Killing corrupted Claude Code instance...[/yellow]")
                tmux_send(pane_target, "\x03")  # Ctrl+C
                time.sleep(0.5)
                tmux_send(pane_target, "\x03")  # Send Ctrl+C again to be sure
                time.sleep(0.5)
                
                # Send exit command in case it's still in Claude Code
                tmux_send(pane_target, "/exit")
                time.sleep(1.0)
                
                # Wait for shell prompt to ensure Claude Code has fully exited
                if not self._wait_for_shell_prompt(pane_target, timeout=10, ignore_shutdown=True):
                    # If still not at shell, try harder
                    tmux_send(pane_target, "\x03")  # Another Ctrl+C
                    time.sleep(1.0)
                    tmux_send(pane_target, "exit")  # Try shell exit command
                    time.sleep(1.0)
                
                # NEVER EVER kill all claude-code processes! This would kill ALL working agents!
                # Just let this specific instance clean up naturally
                time.sleep(2.0)  # Give time for this instance to fully exit

                # Try to restore from backup
                if hasattr(self, "settings_backup_path") and self.settings_backup_path:  # noqa: SIM102
                    if self._restore_claude_settings():
                        console.print(f"[green]Settings restored for agent {agent_id} - retrying launch[/green]")
                        # Wait a bit more to ensure everything is settled
                        time.sleep(2.0)
                        
                        # Return to shell and retry
                        if self._wait_for_shell_prompt(pane_target, timeout=10, ignore_shutdown=True):
                            # Re-acquire lock before retrying
                            if self._acquire_claude_lock(timeout=10.0):
                                try:
                                    tmux_send(pane_target, "cc")
                                    time.sleep(self.wait_after_cc)
                                finally:
                                    self._release_claude_lock()
                                # Continue to next iteration to check again
                                continue
                            else:
                                console.print(f"[red]Agent {agent_id:02d}: Could not acquire lock for retry[/red]")
                        else:
                            console.print(f"[red]Agent {agent_id:02d}: Could not get shell prompt for retry[/red]")

                if self.monitor:
                    self.monitor.agents[agent_id]["status"] = "error"
                    self.monitor.agents[agent_id]["errors"] += 1
                return
            elif "command not found" in content and "cc" in content:
                # cc command doesn't exist
                console.print(f"[red]Agent {agent_id:02d}: 'cc' command not found[/red]")
                if self.monitor:
                    self.monitor.agents[agent_id]["status"] = "error"
                    self.monitor.agents[agent_id]["errors"] += 1
                return
            elif attempt < max_retries - 1:
                # Make this sleep interruptible too
                for _ in range(25):  # 5 seconds in 0.2s intervals
                    if not self.running:
                        return
                    time.sleep(0.2)
            else:
                console.print(
                    f"[red]Agent {agent_id:02d}: Claude Code failed to start properly after {max_retries} attempts[/red]"
                )
                if self.monitor:
                    self.monitor.agents[agent_id]["status"] = "error"
                    self.monitor.agents[agent_id]["errors"] += 1
                return

        # Only send prompt if Claude Code started successfully
        if not claude_started_successfully:
            console.print(f"[red]Agent {agent_id:02d}: Skipping prompt injection - Claude Code not ready[/red]")
            return

        # Send prompt with unique seed for randomization
        seed = randint(100000, 999999)
        
        # Calculate dynamic chunk size and update prompt text if needed
        dynamic_chunk_size = self._calculate_dynamic_chunk_size()
        current_prompt = self.prompt_text
        
        # If dynamic chunk size differs from configured, update the prompt
        configured_chunk = getattr(self, 'chunk_size', 50)
        if dynamic_chunk_size != configured_chunk:
            current_prompt = current_prompt.replace(f'{{{configured_chunk}}}', f'{{{dynamic_chunk_size}}}')
            current_prompt = current_prompt.replace(f'{configured_chunk}', str(dynamic_chunk_size))
            console.print(f"[dim]Agent {agent_id:02d}: Dynamic chunk size: {dynamic_chunk_size} (was {configured_chunk})[/dim]")
        
        # Use regex to handle variations like "random chunks of 50 lines"
        salted_prompt = re.sub(
            r"random chunks(\b.*?\b)?",
            lambda m: f"{m.group(0)} (instance-seed {seed})",
            current_prompt,
            count=1,
            flags=re.IGNORECASE,
        )

        # Send prompt as a single message
        # CRITICAL: Use tmux's literal mode to send the entire prompt correctly
        # This avoids complex line-by-line sending that can cause issues
        prompt_preview = textwrap.shorten(salted_prompt.replace('\n', ' '), width=50, placeholder="...")
        console.print(f"[dim]Agent {agent_id:02d}: Sending {len(salted_prompt)} chars: {prompt_preview}[/dim]")
        
        # Send the entire prompt at once using literal mode
        tmux_send(pane_target, salted_prompt, enter=True)

        if not restart:
            console.print(f"[green]✓ Agent {agent_id:02d}: prompt injected[/green]")

        # Verify prompt was received by checking for working state
        time.sleep(2.0)  # Give Claude a moment to start processing
        verify_content = tmux_capture(pane_target)
        if self.monitor and self.monitor.is_claude_working(verify_content):
            console.print(f"[green]✓ Agent {agent_id:02d}: Claude Code is processing the prompt[/green]")
        else:
            console.print(f"[yellow]⚠ Agent {agent_id:02d}: Claude Code may not have received the prompt properly[/yellow]")

        if self.monitor:
            self.monitor.agents[agent_id]["status"] = "starting"
            self.monitor.agents[agent_id]["last_activity"] = datetime.now()

    def launch_agents(self) -> None:
        """Launch all agents with staggered start times"""
        console.rule("[yellow]Launching agents")

        # Track successful launches to detect corruption patterns
        successful_launches = 0
        last_launch_ok = True  # Track if the previous launch was successful
        current_stagger = self.stagger  # Start with base stagger time

        for i in range(self.agents):
            if not self.running:
                console.print("[yellow]Agent launch interrupted by shutdown signal[/yellow]")
                break

            self.start_agent(i)

            # Check if last agent started successfully
            if self.monitor and i > 0:
                time.sleep(1)  # Brief pause to let status update
                prev_agent_status = self.monitor.agents[i]["status"]
                if prev_agent_status == "error":
                    if last_launch_ok:
                        # Previous launch was OK, but this one failed - double stagger
                        current_stagger = min(current_stagger * 2, 60.0)  # Cap at 60 seconds
                        console.print(f"[yellow]Launch failure detected - increasing stagger to {current_stagger}s[/yellow]")
                    last_launch_ok = False
                else:
                    successful_launches += 1
                    if not last_launch_ok:
                        # Previous launch failed, but this one succeeded - halve stagger
                        current_stagger = max(current_stagger / 2, self.stagger)  # Don't go below base
                        console.print(f"[green]Launch successful - reducing stagger to {current_stagger}s[/green]")
                    last_launch_ok = True

            # Stagger starts to avoid config clobbering
            if i < self.agents - 1 and self.running:
                # Use current_stagger time which adapts based on success/failure
                console.print(f"[dim]Using stagger time: {current_stagger}s[/dim]")

                # Use smaller sleep intervals to be more responsive to shutdown
                for _ in range(int(current_stagger * 5)):
                    if not self.running:
                        break
                    time.sleep(0.2)

        if successful_launches < self.agents:
            console.print(
                f"[yellow]Warning: Only {successful_launches}/{self.agents} agents launched successfully[/yellow]"
            )
            if self.auto_restart:
                console.print("[yellow]Auto-restart enabled - failed agents will be retried[/yellow]")

    def monitor_loop(self) -> None:
        """Main monitoring loop with auto-restart capability"""
        if self.no_monitor:
            console.print("[yellow]Monitoring disabled. Agents will run without supervision.[/yellow]")
            console.print(f"[cyan]Attach with: tmux attach -t {self.session}[/cyan]")
            return

        console.rule("[green]All agents launched - Monitoring active")
        console.print("[yellow]Monitor dashboard running in tmux controller window[/yellow]")
        console.print(f"[cyan]View with: tmux attach -t {self.session}:controller[/cyan]")
        console.print("[cyan]Or use: ./view_agents.sh[/cyan]")
        console.print("[dim]Press Ctrl+C here for graceful shutdown[/dim]\n")

        if self.monitor:
            check_counter = 0

            while self.running:
                # Check agents every N seconds
                if check_counter % self.check_interval == 0:
                    for agent_id in range(self.agents):
                        self.monitor.check_agent(agent_id)

                        # Auto-restart if needed
                        restart_reason = self.monitor.needs_restart(agent_id) if self.auto_restart else None
                        if restart_reason:
                            agent = self.monitor.agents[agent_id]

                            # Implement exponential backoff
                            if agent["last_restart"]:
                                time_since_restart = (datetime.now() - agent["last_restart"]).total_seconds()
                                backoff_time = min(300, 10 * (2 ** agent["restart_count"]))  # Max 5 min

                                if time_since_restart < backoff_time:
                                    continue  # Skip restart, still in backoff period

                            if restart_reason == "context":
                                console.print(
                                    f"[yellow]Low context detected for agent {agent_id}, clearing context…[/yellow]"
                                )
                                self.clear_agent_context(agent_id)
                            else:
                                console.print(
                                    f"[yellow]Restarting agent {agent_id} due to {restart_reason} (attempt #{agent['restart_count'] + 1})…[/yellow]"
                                )
                                self.start_agent(agent_id, restart=True)

                                # Update restart tracking only for full restarts
                                agent["restart_count"] += 1
                                agent["last_restart"] = datetime.now()
                                self.monitor.agents[agent_id] = agent
                            
                            # Track restarts for reporting
                            self.agent_restart_count += 1
                            
                            # Track cycles for incremental commits
                            if self.commit_every and agent["cycles"] > 0:
                                # Check if all agents have completed at least one cycle
                                all_cycles = [self.monitor.agents[i]["cycles"] for i in range(self.agents)]
                                min_cycles = min(all_cycles) if all_cycles else 0
                                
                                # If we've completed N full cycles across all agents, commit
                                if min_cycles > 0 and min_cycles % self.commit_every == 0 and min_cycles > self.regeneration_cycles:
                                    console.print(f"[green]Completed {self.commit_every} regeneration cycles - committing changes[/green]")
                                    self.regeneration_cycles = min_cycles
                                    # Regenerate problems file to update progress
                                    self.regenerate_problems()
                                    # Commit and push
                                    self.commit_and_push()

                # Write state to file for monitor process
                self.write_monitor_state()
                time.sleep(1)
                check_counter += 1

    def run(self) -> None:
        """Main orchestration flow"""
        os.chdir(self.project_path)

        # Display startup banner with custom box style
        # Wrap long project paths for better display
        wrapped_path = textwrap.fill(str(self.project_path), width=60, subsequent_indent="         ")
        
        banner_text = "[bold cyan]Claude Code Agent Farm[/bold cyan]\n"
        banner_text += f"Project: {wrapped_path}\n"
        banner_text += f"Agents: {self.agents}\n"
        banner_text += f"Session: {self.session}\n"
        banner_text += f"Auto-restart: {'enabled' if self.auto_restart else 'disabled'}"
        if self.commit_every:
            banner_text += f"\nIncremental commits: every {self.commit_every} cycles"
        
        console.print(
            Panel.fit(
                banner_text,
                border_style="cyan",
                box=box.DOUBLE,  # Use double-line box for main banner
            )
        )

        # Backup Claude settings before starting
        self.settings_backup_path = self._backup_claude_settings()
        
        # Check current permissions are correct
        self._check_claude_permissions()
        
        # Copy best practices guides if configured
        self._copy_best_practices_guides()

        # Ensure generated artefacts are ignored by git
        self._ensure_gitignore_entries()

        try:
            # Execute workflow steps
            self.regenerate_problems()
            self.commit_and_push()
            self.setup_tmux_session()

            # Initialize monitor
            self.monitor = AgentMonitor(
                self.session,
                self.agents,
                self.pane_mapping,
                context_threshold=self.context_threshold,
                idle_timeout=self.idle_timeout,
                max_errors=self.max_errors,
                project_path=self.project_path,
            )

            # Launch agents
            self.launch_agents()

            # Start monitoring
            self.monitor_loop()

            # Attach to session if requested
            if self.attach and not self.no_monitor:
                run(f"tmux attach-session -t {self.session}", check=False)

        except KeyboardInterrupt:
            # Don't print anything here - let the main handler deal with it
            raise

    def shutdown(self) -> None:
        """Clean shutdown of all agents"""
        console.print("\n[yellow]Shutting down agents...[/yellow]")

        for i in range(self.agents):
            pane_target = self.pane_mapping.get(i)
            if pane_target:
                tmux_send(pane_target, "/exit", update_heartbeat=False)

        time.sleep(2)

        if getattr(self, "tmux_kill_on_exit", True):
            run(f"tmux kill-session -t {self.session}", check=False, quiet=True)
            console.print("[green]✓ tmux session terminated[/green]")
        else:
            console.print("[yellow]tmux left running (tmux_kill_on_exit = false)[/yellow]")

        # Clean up state file
        if hasattr(self, "state_file") and self.state_file.exists():
            self.state_file.unlink()
            console.print("[green]✓ Monitor state file cleaned up[/green]")
        
        # Clean up heartbeat files
        heartbeats_dir = self.project_path / ".heartbeats"
        if heartbeats_dir.exists():
            for hb_file in heartbeats_dir.glob("agent*.heartbeat"):
                hb_file.unlink(missing_ok=True)
            try:
                heartbeats_dir.rmdir()  # Remove directory if empty
                console.print("[green]✓ Heartbeat files cleaned up[/green]")
            except OSError:
                # Directory not empty or other error
                pass

        # Generate HTML report before final cleanup
        self.generate_html_report()
        
        # Restore font size if we changed it
        if hasattr(self, "_zoom_adjusted") and self._zoom_adjusted:
            console.print("[dim]Note: You may want to restore zoom with Ctrl/Cmd + 0[/dim]")

    def _emergency_cleanup(self) -> None:
        """Emergency cleanup handler for unexpected exits"""
        with contextlib.suppress(Exception):
            # Kill the tmux session if it exists
            run(f"tmux kill-session -t {self.session}", check=False, quiet=True)
            # Clean up state file
            if hasattr(self, "state_file") and self.state_file.exists():
                self.state_file.unlink()
            # Clean up lock file
            lock_file = Path.home() / ".claude" / ".agent_farm_launch.lock"
            if lock_file.exists():
                lock_file.unlink()

    def generate_html_report(self) -> None:
        """Generate single-file HTML run report with all statistics"""
        try:
            # Calculate run duration
            run_duration = datetime.now() - self.run_start_time
            hours, remainder = divmod(int(run_duration.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{hours}h {minutes}m {seconds}s"
            
            # Gather agent statistics if monitor is available
            agent_stats = []
            total_cycles = 0
            if self.monitor:
                for agent_id, agent in self.monitor.agents.items():
                    agent_stats.append({
                        "id": agent_id,
                        "status": agent["status"],
                        "cycles": agent["cycles"],
                        "errors": agent["errors"],
                        "restarts": agent["restart_count"],
                        "context": agent["last_context"],
                    })
                    total_cycles += agent["cycles"]
            
            # Count initial problems
            initial_problems = 0
            if self.combined_file.exists():
                initial_problems = line_count(self.combined_file)
            
            # Generate HTML using Rich's console
            html_console = Console(record=True, width=120)
            
            # Title
            html_console.print(Panel.fit(
                f"[bold cyan]Claude Code Agent Farm - Run Report[/bold cyan]\n"
                f"Project: {self.project_path.name}\n"
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                border_style="cyan"
            ))
            
            # Summary statistics
            html_console.print("\n[bold]Run Summary[/bold]")
            summary_table = Table(box=box.ROUNDED)
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", style="green")
            
            summary_table.add_row("Duration", duration_str)
            summary_table.add_row("Agents Used", str(self.agents))
            summary_table.add_row("Total Cycles", str(total_cycles))
            summary_table.add_row("Problems Fixed", str(self.total_problems_fixed))
            summary_table.add_row("Commits Made", str(self.total_commits_made))
            summary_table.add_row("Agent Restarts", str(self.agent_restart_count))
            summary_table.add_row("Initial Problems", str(initial_problems))
            remaining_problems = initial_problems - self.total_problems_fixed
            summary_table.add_row("Remaining Problems", str(max(0, remaining_problems)))
            
            html_console.print(summary_table)
            
            # Agent details
            if agent_stats:
                html_console.print("\n[bold]Agent Performance[/bold]")
                agent_table = Table(box=box.ROUNDED)
                agent_table.add_column("Agent", style="cyan", width=10)
                agent_table.add_column("Status", style="green", width=10)
                agent_table.add_column("Cycles", style="yellow", width=8)
                agent_table.add_column("Context %", style="magenta", width=10)
                agent_table.add_column("Errors", style="red", width=8)
                agent_table.add_column("Restarts", style="orange1", width=10)
                
                for agent in sorted(agent_stats, key=lambda x: x["id"]):
                    status_color = {
                        "working": "green",
                        "ready": "cyan",
                        "idle": "yellow",
                        "error": "red",
                        "starting": "yellow",
                        "unknown": "dim"
                    }.get(agent["status"], "white")
                    
                    agent_table.add_row(
                        f"Agent {agent['id']:02d}",
                        f"[{status_color}]{agent['status']}[/]",
                        str(agent["cycles"]),
                        f"{agent['context']}%",
                        str(agent["errors"]),
                        str(agent["restarts"])
                    )
                
                html_console.print(agent_table)
            
            # Configuration used
            html_console.print("\n[bold]Configuration[/bold]")
            config_items = [
                ("Tech Stack", getattr(self, 'tech_stack', 'unknown')),
                ("Chunk Size", str(getattr(self, 'chunk_size', 50))),
                ("Context Threshold", f"{self.context_threshold}%"),
                ("Idle Timeout", f"{self.idle_timeout}s"),
                ("Auto Restart", "Yes" if self.auto_restart else "No"),
                ("Skip Regenerate", "Yes" if self.skip_regenerate else "No"),
                ("Skip Commit", "Yes" if self.skip_commit else "No"),
            ]
            
            for key, value in config_items:
                html_console.print(f"  {key}: [cyan]{value}[/cyan]")
            
            # Save HTML report
            report_file = self.project_path / f"agent_farm_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            html_content = html_console.export_html(inline_styles=True)
            
            # Add some custom CSS for better formatting
            custom_css = """
            <style>
                body {
                    font-family: 'Cascadia Code', 'Fira Code', monospace;
                    background-color: #0d1117;
                    color: #c9d1d9;
                    padding: 20px;
                    line-height: 1.6;
                }
                pre {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 16px;
                    overflow-x: auto;
                }
            </style>
            """
            
            # Insert custom CSS after <head>
            html_content = html_content.replace("<head>", f"<head>{custom_css}")
            
            report_file.write_text(html_content)
            console.print(f"\n[green]✓ Generated run report: {report_file.name}[/green]")
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not generate HTML report: {e}[/yellow]")
    
    def write_monitor_state(self) -> None:
        """Write current monitor state to shared file"""
        if not self.monitor:
            return

        def _serialise_agent(a: dict) -> dict:
            """Convert datetime objects to ISO strings for JSON serialization"""
            return {
                **a,
                "start_time": a["start_time"].isoformat(),
                "last_activity": a["last_activity"].isoformat(),
                "last_restart": a["last_restart"].isoformat() if a.get("last_restart") is not None else None,
                "last_heartbeat": a["last_heartbeat"].isoformat() if a.get("last_heartbeat") is not None else None,
                "cycle_start_time": a["cycle_start_time"].isoformat() if a.get("cycle_start_time") is not None else None,
            }

        state_data = {
            "session": self.session,
            "num_agents": self.agents,
            "agents": {str(k): _serialise_agent(v) for k, v in self.monitor.agents.items()},
            "start_time": self.monitor.start_time.isoformat(),
            "timestamp": datetime.now().isoformat(),
        }

        # Write atomically with file locking
        tmp_file = self.state_file.with_suffix(".tmp")
        try:
            with tmp_file.open("w") as f:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(state_data, f)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    # Release lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic rename
            tmp_file.replace(self.state_file)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not write monitor state: {e}[/yellow]")
            tmp_file.unlink(missing_ok=True)

    def _ensure_gitignore_entries(self) -> None:
        """Add Claude Agent Farm generated artefacts to the project's .gitignore (idempotent)"""
        # Only act if this is a git repository
        if not (self.project_path / ".git").exists():
            return

        ignore_path = self.project_path / ".gitignore"

        # Patterns we never want committed
        patterns = [
            "# Claude Agent Farm",  # marker comment
            ".heartbeats/",
            ".claude_agent_farm_state.json",
            ".claude_agent_farm_backups/",
            "agent_farm_report_*.html",
        ]

        if not ignore_path.exists():
            # Create new file with our entries
            ignore_path.write_text("\n".join(patterns) + "\n")
            console.print("[green]✓ Created .gitignore with Claude Agent Farm entries[/green]")
            return

        # Read existing lines
        existing = ignore_path.read_text().splitlines()
        # Determine which patterns are missing (skip marker comment when checking)
        missing = [p for p in patterns[1:] if p not in existing]

        if missing:
            with ignore_path.open("a") as f:
                # Add comment if not already present
                if patterns[0] not in existing:
                    f.write("\n" + patterns[0] + "\n")
                for p in missing:
                    f.write(p + "\n")
            console.print(f"[green]✓ Added {len(missing)} Claude Agent Farm pattern(s) to .gitignore[/green]")

    def clear_agent_context(self, agent_id: int) -> None:
        """Send /clear to the specified agent and re-inject the working prompt.

        This avoids fully restarting Claude Code, preventing settings races
        while still recovering context budget.
        """
        pane_target = self.pane_mapping.get(agent_id)
        if not pane_target:
            console.print(f"[red]Error: No pane mapping found for agent {agent_id}[/red]")
            return

        console.print(f"[yellow]Clearing context for agent {agent_id}…[/yellow]")

        # Instruct Claude Code to compact its context
        tmux_send(pane_target, "/clear")

        # Give Claude a moment to process the command
        for _ in range(10):  # ~2 s total, but abort early if shutting down
            if not self.running:
                return
            time.sleep(0.2)

        # Update bookkeeping so the monitor shows fresh state
        if self.monitor:
            agent = self.monitor.agents[agent_id]
            agent["cycles"] += 1
            agent["last_context"] = 100  # assume cleared
            agent["last_activity"] = datetime.now()

        # Re-inject the prompt with a unique seed so each cycle is distinct
        seed = randint(100000, 999999)
        dynamic_chunk_size = self._calculate_dynamic_chunk_size()
        current_prompt = self.prompt_text
        configured_chunk = getattr(self, "chunk_size", 50)
        if dynamic_chunk_size != configured_chunk:
            current_prompt = current_prompt.replace(f"{{{configured_chunk}}}", f"{{{dynamic_chunk_size}}}")
            current_prompt = current_prompt.replace(f"{configured_chunk}", str(dynamic_chunk_size))

        salted_prompt = re.sub(
            r"random chunks(\b.*?\b)?",
            lambda m: f"{m.group(0)} (instance-seed {seed})",
            current_prompt,
            count=1,
            flags=re.IGNORECASE,
        )

        tmux_send(pane_target, salted_prompt, enter=True)
        console.print(f"[green]✓ Agent {agent_id:02d}: context cleared and prompt re-injected[/green]")


# ─────────────────────────────── CLI Entry Point ──────────────────────────── #


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    path: str = typer.Option(..., "--path", help="Absolute path to project root", rich_help_panel="Required Arguments"),
    agents: int = typer.Option(
        20, "--agents", "-n", help="Number of Claude agents", rich_help_panel="Agent Configuration"
    ),
    session: str = typer.Option(
        "claude_agents", "--session", "-s", help="tmux session name", rich_help_panel="Agent Configuration"
    ),
    stagger: float = typer.Option(
        10.0, "--stagger", help="Seconds between starting agents", rich_help_panel="Timing Configuration"
    ),
    wait_after_cc: float = typer.Option(
        15.0, "--wait-after-cc", help="Seconds to wait after launching cc", rich_help_panel="Timing Configuration"
    ),
    check_interval: int = typer.Option(
        10, "--check-interval", help="Seconds between agent health checks", rich_help_panel="Timing Configuration"
    ),
    skip_regenerate: bool = typer.Option(
        False, "--skip-regenerate", help="Skip regenerating problems file", rich_help_panel="Feature Flags"
    ),
    skip_commit: bool = typer.Option(
        False, "--skip-commit", help="Skip git commit/push", rich_help_panel="Feature Flags"
    ),
    auto_restart: bool = typer.Option(
        False, "--auto-restart", help="Auto-restart agents on errors/completion", rich_help_panel="Feature Flags"
    ),
    no_monitor: bool = typer.Option(
        False, "--no-monitor", help="Disable monitoring (just launch and exit)", rich_help_panel="Feature Flags"
    ),
    attach: bool = typer.Option(
        False, "--attach", help="Attach to tmux session after setup", rich_help_panel="Feature Flags"
    ),
    prompt_file: Optional[str] = typer.Option(
        None, "--prompt-file", help="Path to custom prompt file", rich_help_panel="Advanced Options"
    ),
    config: Optional[str] = typer.Option(
        None, "--config", help="Load settings from JSON config file", rich_help_panel="Advanced Options"
    ),
    context_threshold: int = typer.Option(
        20,
        "--context-threshold",
        help="Restart agent when context ≤ this percentage",
        rich_help_panel="Advanced Options",
    ),
    idle_timeout: int = typer.Option(
        60,
        "--idle-timeout",
        help="Seconds of inactivity before marking agent as idle",
        rich_help_panel="Advanced Options",
    ),
    max_errors: int = typer.Option(
        3, "--max-errors", help="Maximum consecutive errors before disabling agent", rich_help_panel="Advanced Options"
    ),
    tmux_kill_on_exit: bool = typer.Option(
        True,
        "--tmux-kill-on-exit/--no-tmux-kill-on-exit",
        help="Kill tmux session on exit",
        rich_help_panel="Advanced Options",
    ),
    tmux_mouse: bool = typer.Option(
        True, "--tmux-mouse/--no-tmux-mouse", help="Enable tmux mouse support", rich_help_panel="Advanced Options"
    ),
    fast_start: bool = typer.Option(
        False, "--fast-start", help="Skip shell prompt checking", rich_help_panel="Advanced Options"
    ),
    full_backup: bool = typer.Option(
        False, "--full-backup", help="Perform a full backup before starting", rich_help_panel="Advanced Options"
    ),
    commit_every: Optional[int] = typer.Option(
        None, "--commit-every", help="Commit after every N regeneration cycles", rich_help_panel="Advanced Options"
    ),
) -> None:
    """
    Claude Code Agent Farm - Parallel code fixing automation

    This tool orchestrates multiple Claude Code agents working in parallel
    to fix type-checker and linter problems in your codebase.
    """
    # If a subcommand was invoked, don't run the main logic
    if ctx.invoked_subcommand is not None:
        return

    # Validate project path
    project_path = Path(path).expanduser().resolve()
    if not project_path.is_dir():
        console.print(f"[red]✖ {project_path} is not a directory[/red]")
        raise typer.Exit(1)

    # Validate agent count
    if agents < 1:
        console.print("[red]✖ Number of agents must be at least 1[/red]")
        raise typer.Exit(1)

    if agents > 50:
        console.print(f"[yellow]⚠ Running {agents} agents may consume significant resources[/yellow]")
        if not interruptible_confirm("Do you want to continue?"):
            raise KeyboardInterrupt()

    # Create and run the orchestrator
    farm = ClaudeAgentFarm(
        path=path,
        agents=agents,
        session=session,
        stagger=stagger,
        wait_after_cc=wait_after_cc,
        check_interval=check_interval,
        skip_regenerate=skip_regenerate,
        skip_commit=skip_commit,
        auto_restart=auto_restart,
        no_monitor=no_monitor,
        attach=attach,
        prompt_file=prompt_file,
        config=config,
        context_threshold=context_threshold,
        idle_timeout=idle_timeout,
        max_errors=max_errors,
        tmux_kill_on_exit=tmux_kill_on_exit,
        tmux_mouse=tmux_mouse,
        fast_start=fast_start,
        full_backup=full_backup,
        commit_every=commit_every,
    )

    try:
        farm.run()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user[/red]")
    except Exception as e:
        # Wrap long error messages for better readability
        error_msg = textwrap.fill(str(e), width=80, initial_indent="Error: ", subsequent_indent="       ")
        console.print(f"[red]{error_msg}[/red]")
        import traceback

        traceback.print_exc()
    finally:
        farm.shutdown()


@app.command(name="monitor-only", hidden=True)
def monitor_only(
    path: str = typer.Option(..., "--path", help="Absolute path to project root"),
    session: str = typer.Option("claude_agents", "--session", "-s", help="tmux session name"),
) -> None:
    """Run monitor display only - internal command used by the orchestrator"""
    project_path = Path(path).expanduser().resolve()
    state_file = project_path / MONITOR_STATE_FILE

    console.print(
        Panel.fit(
            f"[bold cyan]Claude Agent Farm Monitor[/bold cyan]\nSession: {session}\nPress Ctrl+C to exit monitor view",
            border_style="cyan",
            box=box.DOUBLE_EDGE,  # Use double-edge box for monitor panel
        )
    )

    with Live(console=console, refresh_per_second=1) as live:
        while True:
            try:
                if state_file.exists():
                    # Use file locking when reading to avoid race conditions
                    try:
                        with state_file.open() as f:
                            # Try to acquire shared lock (non-exclusive)
                            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                            try:
                                state_data = json.load(f)
                            finally:
                                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except (IOError, OSError) as e:
                        raise Exception(f"Failed to read state file: {e}") from e

                    # Recreate table from state data
                    table = Table(
                        title=f"Claude Agent Farm - {datetime.now().strftime('%H:%M:%S')}",
                        box=box.ROUNDED,  # Consistent box style with main status table
                    )
                    table.add_column("Agent", style="cyan", width=8)
                    table.add_column("Status", style="green", width=10)
                    table.add_column("Cycles", style="yellow", width=6)
                    table.add_column("Context", style="magenta", width=8)
                    table.add_column("Runtime", style="blue", width=12)
                    table.add_column("Errors", style="red", width=6)

                    agents = state_data.get("agents", {})

                    for agent_id in sorted(int(k) for k in agents):
                        agent = agents[str(agent_id)]
                        agent_start = datetime.fromisoformat(agent["start_time"])
                        runtime = str(datetime.now() - agent_start).split(".")[0]

                        status_style = {
                            "working": "[green]",
                            "ready": "[cyan]",
                            "idle": "[yellow]",
                            "error": "[red]",
                            "starting": "[yellow]",
                            "unknown": "[dim]",
                        }.get(agent["status"], "")

                        table.add_row(
                            f"Pane {agent_id:02d}",
                            f"{status_style}{agent['status']}[/]",
                            str(agent["cycles"]),
                            f"{agent['last_context']}%",
                            runtime,
                            str(agent["errors"]),
                        )

                    live.update(table)
                else:
                    live.update("[yellow]Waiting for monitor data...[/yellow]")

                time.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                # Wrap error messages for monitor display
                wrapped_error = textwrap.fill(f"Error reading state: {e}", width=60)
                live.update(f"[red]{wrapped_error}[/red]")
                time.sleep(1)


@app.command(name="doctor")
def doctor(
    path: Optional[str] = typer.Option(None, "--path", help="Project path to check (optional)"),
) -> None:
    """Pre-flight verifier to check system configuration and catch common setup errors"""
    console.print(
        Panel.fit(
            "[bold cyan]Claude Agent Farm Doctor[/bold cyan]\nChecking system configuration...",
            border_style="cyan",
            box=box.DOUBLE,
        )
    )
    
    issues_found = 0
    warnings_found = 0
    
    # Helper function to check if command exists
    def command_exists(cmd: str) -> bool:
        """Check if a command exists in PATH"""
        try:
            result = subprocess.run(["which", cmd], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    # 1. Check Python version
    console.print("\n[bold]1. Python Version[/bold]")
    py_version = sys.version_info
    if py_version >= (3, 13):
        console.print(f"  ✅ Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    else:
        console.print(f"  ❌ Python {py_version.major}.{py_version.minor}.{py_version.micro} (requires 3.13+)")
        issues_found += 1
    
    # 2. Check tmux
    console.print("\n[bold]2. tmux Installation[/bold]")
    if command_exists("tmux"):
        ret, stdout, _ = run("tmux -V", capture=True, quiet=True)
        if ret == 0:
            console.print(f"  ✅ {stdout.strip()}")
        else:
            console.print("  ❌ tmux found but version check failed")
            issues_found += 1
    else:
        console.print("  ❌ tmux not found in PATH")
        issues_found += 1
    
    # 3. Check cc alias
    console.print("\n[bold]3. Claude Code Alias[/bold]")
    # Check in bash
    bash_has_cc = False
    try:
        ret, stdout, _ = run("bash -i -c 'alias cc 2>/dev/null'", capture=True, quiet=True)
        if ret == 0 and "claude" in stdout and "--dangerously-skip-permissions" in stdout:
            bash_has_cc = True
    except Exception:
        pass
    
    # Check in zsh if it exists
    zsh_has_cc = False
    if Path(os.path.expanduser("~/.zshrc")).exists():
        try:
            ret, stdout, _ = run("zsh -i -c 'alias cc 2>/dev/null'", capture=True, quiet=True)
            if ret == 0 and "claude" in stdout and "--dangerously-skip-permissions" in stdout:
                zsh_has_cc = True
        except Exception:
            pass
    
    if bash_has_cc or zsh_has_cc:
        console.print("  ✅ cc alias configured correctly")
        if bash_has_cc:
            console.print("     - Found in bash")
        if zsh_has_cc:
            console.print("     - Found in zsh")
    else:
        console.print("  ❌ cc alias not configured or incorrect")
        console.print("     Expected: alias cc=\"ENABLE_BACKGROUND_TASKS=1 claude --dangerously-skip-permissions\"")
        issues_found += 1
    
    # 4. Check Claude Code installation
    console.print("\n[bold]4. Claude Code Installation[/bold]")
    if command_exists("claude"):
        console.print("  ✅ claude command found")
    else:
        console.print("  ❌ claude command not found in PATH")
        issues_found += 1
    
    # 5. Check Anthropic API key
    console.print("\n[bold]5. Anthropic API Configuration[/bold]")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        console.print(f"  ✅ ANTHROPIC_API_KEY set ({len(api_key)} chars)")
    else:
        # Check Claude settings file
        claude_settings = Path.home() / ".claude" / "settings.json"
        if claude_settings.exists():
            try:
                with claude_settings.open() as f:
                    settings = json.load(f)
                    if settings.get("apiKey") or settings.get("anthropicApiKey"):
                        console.print("  ✅ API key found in Claude settings")
                    else:
                        console.print("  ⚠️  No API key in environment or Claude settings")
                        warnings_found += 1
            except Exception:
                console.print("  ⚠️  Could not read Claude settings")
                warnings_found += 1
        else:
            console.print("  ⚠️  No API key in environment and no Claude settings found")
            warnings_found += 1
    
    # 6. Check git
    console.print("\n[bold]6. Git Configuration[/bold]")
    if command_exists("git"):
        ret, stdout, _ = run("git --version", capture=True, quiet=True)
        if ret == 0:
            console.print(f"  ✅ {stdout.strip()}")
        else:
            console.print("  ❌ git found but version check failed")
            issues_found += 1
    else:
        console.print("  ❌ git not found in PATH")
        issues_found += 1
    
    # 7. Check uv (package manager)
    console.print("\n[bold]7. uv Package Manager[/bold]")
    if command_exists("uv"):
        ret, stdout, _ = run("uv --version", capture=True, quiet=True)
        if ret == 0:
            console.print(f"  ✅ {stdout.strip()}")
        else:
            console.print("  ⚠️  uv found but version check failed")
            warnings_found += 1
    else:
        console.print("  ⚠️  uv not found (recommended for Python projects)")
        warnings_found += 1
    
    # 8. Check project-specific tools if path provided
    if path:
        project_path = Path(path).expanduser().resolve()
        if project_path.is_dir():
            console.print(f"\n[bold]8. Project-Specific Checks ({project_path.name})[/bold]")
            
            # Check for config files
            config_files = list(project_path.glob("configs/*.json"))
            if config_files:
                console.print(f"  ✅ Found {len(config_files)} config files")
            else:
                console.print("  ⚠️  No config files found in configs/")
                warnings_found += 1
            
            # Check for prompt files
            prompt_files = list(project_path.glob("prompts/*.txt"))
            if prompt_files:
                console.print(f"  ✅ Found {len(prompt_files)} prompt files")
            else:
                console.print("  ⚠️  No prompt files found in prompts/")
                warnings_found += 1
            
            # Try to detect project type and check tools
            if (project_path / "package.json").exists():
                console.print("  📦 Detected Node.js project")
                for tool in ["node", "npm", "bun"]:
                    if command_exists(tool):
                        console.print(f"     ✅ {tool} available")
                    else:
                        console.print(f"     ⚠️  {tool} not found")
                        warnings_found += 1
            
            if (project_path / "pyproject.toml").exists():
                console.print("  🐍 Detected Python project")
                for tool in ["python3", "mypy", "ruff"]:
                    if command_exists(tool):
                        console.print(f"     ✅ {tool} available")
                    else:
                        console.print(f"     ⚠️  {tool} not found")
                        warnings_found += 1
        else:
            console.print("\n[bold]8. Project Path[/bold]")
            console.print(f"  ❌ Invalid project path: {path}")
            issues_found += 1
    
    # 9. Check permissions
    console.print("\n[bold]9. File Permissions[/bold]")
    claude_dir = Path.home() / ".claude"
    if claude_dir.exists():
        # Check directory permissions
        dir_perms = oct(claude_dir.stat().st_mode)[-3:]
        if dir_perms in ("700", "755"):
            console.print(f"  ✅ ~/.claude permissions: {dir_perms}")
        else:
            console.print(f"  ⚠️  ~/.claude permissions: {dir_perms} (expected 700)")
            warnings_found += 1
        
        # Check settings.json permissions
        settings_file = claude_dir / "settings.json"
        if settings_file.exists():
            file_perms = oct(settings_file.stat().st_mode)[-3:]
            if file_perms == "600":
                console.print(f"  ✅ settings.json permissions: {file_perms}")
            else:
                console.print(f"  ⚠️  settings.json permissions: {file_perms} (expected 600)")
                warnings_found += 1
    
    # 10. Check for common issues
    console.print("\n[bold]10. Common Issues Check[/bold]")
    
    # Check for stale lock files
    lock_file = Path.home() / ".claude" / ".agent_farm_launch.lock"
    if lock_file.exists():
        age = time.time() - lock_file.stat().st_mtime
        if age > 300:  # 5 minutes
            console.print(f"  ⚠️  Stale lock file found ({age:.0f}s old)")
            console.print("     Run: rm ~/.claude/.agent_farm_launch.lock")
            warnings_found += 1
        else:
            console.print("  ✅ No stale lock files")
    else:
        console.print("  ✅ No lock files present")
    
    # Summary
    console.print("\n" + "─" * 60)
    if issues_found == 0 and warnings_found == 0:
        console.print("\n[bold green]✅ All checks passed![/bold green]")
        console.print("Your system is ready to run Claude Agent Farm.")
    elif issues_found > 0:
        console.print(f"\n[bold red]❌ Found {issues_found} critical issues and {warnings_found} warnings[/bold red]")
        console.print("Please fix the critical issues before running the agent farm.")
    else:
        console.print(f"\n[bold yellow]⚠️  Found {warnings_found} warnings (no critical issues)[/bold yellow]")
        console.print("The agent farm should work, but fixing warnings is recommended.")
    
    # Exit with appropriate code
    if issues_found > 0:
        raise typer.Exit(1)
    elif warnings_found > 0:
        raise typer.Exit(0)  # Warnings are not fatal


@app.command()
def install_completion(
    shell: Optional[str] = typer.Option(None, help="Shell to install completion for. Auto-detected if not provided.")
) -> None:
    """Install shell completion for claude-code-agent-farm command"""
    import platform
    import subprocess
    
    # Auto-detect shell if not provided
    if shell is None:
        if platform.system() == "Windows":
            console.print("[yellow]Shell completion is not supported on Windows[/yellow]")
            raise typer.Exit(1)
        
        # Try to detect shell from environment
        shell_env = os.environ.get("SHELL", "").lower()
        if "bash" in shell_env:
            shell = "bash"
        elif "zsh" in shell_env:
            shell = "zsh"
        elif "fish" in shell_env:
            shell = "fish"
        else:
            console.print("[yellow]Could not auto-detect shell. Please specify with --shell[/yellow]")
            console.print("Supported shells: bash, zsh, fish")
            raise typer.Exit(1)
    
    # Validate shell
    shell = shell.lower()
    if shell not in ["bash", "zsh", "fish"]:
        console.print(f"[red]Unsupported shell: {shell}[/red]")
        console.print("Supported shells: bash, zsh, fish")
        raise typer.Exit(1)
    
    console.print(f"[bold]Installing completion for {shell}...[/bold]")
    
    try:
        # Generate completion script
        completion_script = subprocess.check_output(
            ["claude-code-agent-farm", "--show-completion", shell],
            text=True
        )
        
        # Determine where to install
        if shell == "bash":
            # Try to install to bash-completion directory
            completion_dirs = [
                "/etc/bash_completion.d",
                "/usr/local/etc/bash_completion.d",
                f"{Path.home()}/.local/share/bash-completion/completions",
            ]
            
            installed = False
            for comp_dir in completion_dirs:
                comp_path = Path(comp_dir)
                if comp_path.exists() and os.access(comp_path, os.W_OK):
                    comp_file = comp_path / "claude-code-agent-farm"
                    comp_file.write_text(completion_script)
                    console.print(f"[green]✓ Installed completion to {comp_file}[/green]")
                    installed = True
                    break
            
            if not installed:
                # Fall back to .bashrc
                bashrc = Path.home() / ".bashrc"
                if bashrc.exists():
                    # Check if already installed
                    bashrc_content = bashrc.read_text()
                    if "claude-code-agent-farm completion" not in bashrc_content:
                        with bashrc.open("a") as f:
                            f.write("\n# Claude Code Agent Farm completion\n")
                            f.write(completion_script)
                            f.write("\n")
                        console.print(f"[green]✓ Added completion to {bashrc}[/green]")
                    else:
                        console.print(f"[yellow]Completion already installed in {bashrc}[/yellow]")
                else:
                    console.print("[red]Could not find .bashrc[/red]")
                    raise typer.Exit(1)
            
            console.print("[dim]Run 'source ~/.bashrc' or start a new shell to use completion[/dim]")
            
        elif shell == "zsh":
            # Install to zsh completions directory
            comp_dirs = [
                "/usr/local/share/zsh/site-functions",
                "/usr/share/zsh/site-functions",
                f"{Path.home()}/.zsh/completions",
            ]
            
            installed = False
            for comp_dir in comp_dirs:
                comp_path = Path(comp_dir)
                if comp_path.exists() and os.access(comp_path, os.W_OK):
                    comp_file = comp_path / "_claude-code-agent-farm"
                    comp_file.write_text(completion_script)
                    console.print(f"[green]✓ Installed completion to {comp_file}[/green]")
                    installed = True
                    break
            
            if not installed:
                # Create user completions directory
                user_comp_dir = Path.home() / ".zsh" / "completions"
                user_comp_dir.mkdir(parents=True, exist_ok=True)
                comp_file = user_comp_dir / "_claude-code-agent-farm"
                comp_file.write_text(completion_script)
                console.print(f"[green]✓ Installed completion to {comp_file}[/green]")
                
                # Check if this directory is in fpath
                zshrc = Path.home() / ".zshrc"
                if zshrc.exists():
                    zshrc_content = zshrc.read_text()
                    if str(user_comp_dir) not in zshrc_content:
                        with zshrc.open("a") as f:
                            f.write("\n# Add claude-code-agent-farm completions\n")
                            f.write(f"fpath=({user_comp_dir} $fpath)\n")
                            f.write("autoload -Uz compinit && compinit\n")
                        console.print(f"[green]✓ Updated {zshrc} to include completion directory[/green]")
            
            console.print("[dim]Run 'source ~/.zshrc' or start a new shell to use completion[/dim]")
            
        elif shell == "fish":
            # Install to fish completions directory
            fish_comp_dir = Path.home() / ".config" / "fish" / "completions"
            fish_comp_dir.mkdir(parents=True, exist_ok=True)
            comp_file = fish_comp_dir / "claude-code-agent-farm.fish"
            comp_file.write_text(completion_script)
            console.print(f"[green]✓ Installed completion to {comp_file}[/green]")
            console.print("[dim]Completion will be available in new fish shells[/dim]")
        
        console.print("\n[bold green]Shell completion installed successfully![/bold green]")
        console.print("You can now use Tab to complete commands and options.")
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to generate completion script: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Failed to install completion: {e}[/red]")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
