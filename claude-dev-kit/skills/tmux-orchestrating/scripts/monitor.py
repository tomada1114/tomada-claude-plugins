#!/usr/bin/env python3
"""
tmux-orchestrating: Live monitoring dashboard.

Run in a SEPARATE terminal to monitor orchestration progress in real-time.

Usage:
    python3 monitor.py [SESSION_NAME] [WORKER_COUNT] [WORK_DIR]

    SESSION_NAME:  tmux session name (default: orchestration)
    WORKER_COUNT:  number of workers (default: 2)
    WORK_DIR:      working directory containing queue/ (default: current dir)

Example:
    # In a separate terminal:
    python3 ~/.claude/skills/tmux-orchestrating/scripts/monitor.py
    python3 ~/.claude/skills/tmux-orchestrating/scripts/monitor.py orchestration 3 /path/to/project
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

SCRIPT_DIR = Path(__file__).parent
CHECK_STATUS_SH = SCRIPT_DIR / "check-status.sh"
REFRESH_INTERVAL = 3

STATUS_STYLES = {
    "Complete": "bold green",
    "Running": "bold yellow",
    "Idle": "dim white",
    "Unknown": "dim red",
    "NoSession": "bold red",
}

STATUS_ICONS = {
    "Complete": "[green]✔[/green]",
    "Running": "[yellow]⟳[/yellow]",
    "Idle": "[dim]○[/dim]",
    "Unknown": "[red]?[/red]",
    "NoSession": "[red]✖[/red]",
}

PROGRESS_FILLED = "█"
PROGRESS_EMPTY = "░"


def get_status(session: str, worker_count: int, work_dir: str) -> dict | None:
    """Run check-status.sh --json and parse the output."""
    try:
        result = subprocess.run(
            ["bash", str(CHECK_STATUS_SH), session, str(worker_count), "--json"],
            capture_output=True,
            text=True,
            cwd=work_dir,
            timeout=10,
        )
        return json.loads(result.stdout.strip())
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def build_progress_bar(completed: int, total: int, width: int = 20) -> str:
    """Build a text progress bar."""
    if total == 0:
        return PROGRESS_EMPTY * width
    filled = int(width * completed / total)
    return PROGRESS_FILLED * filled + PROGRESS_EMPTY * (width - filled)


def read_file_preview(path: Path, max_lines: int = 8) -> str:
    """Read first N lines of a file."""
    try:
        lines = path.read_text().strip().splitlines()[:max_lines]
        return "\n".join(lines)
    except (FileNotFoundError, PermissionError):
        return "(not found)"


def build_header(data: dict) -> Panel:
    """Build the header panel."""
    mode = data.get("mode", "unknown")
    session = data.get("session", "?")
    goal = data.get("goal", "")
    session_exists = data.get("session_exists", False)
    now = datetime.now().strftime("%H:%M:%S")

    mode_display = (
        "[cyan]Orchestrated[/cyan]" if mode == "orchestrated" else "[blue]Quick[/blue]"
    )
    session_display = (
        f"[green]{session}[/green]"
        if session_exists
        else f"[red]{session} (not found)[/red]"
    )

    header_text = Text()
    header_text.append(f"  Mode: ", style="dim")
    header_text.append_text(Text.from_markup(mode_display))
    header_text.append(f"  │  Session: ", style="dim")
    header_text.append_text(Text.from_markup(session_display))
    header_text.append(f"  │  Updated: {now}", style="dim")

    if goal:
        header_text.append(f"\n  Goal: ", style="dim")
        header_text.append(goal[:80], style="bold")

    return Panel(header_text, title="[bold]tmux-orchestrating Monitor[/bold]", border_style="cyan")


def build_workers_table(data: dict) -> Table:
    """Build the workers status table."""
    table = Table(expand=True, show_header=True, header_style="bold")
    table.add_column("", width=3, justify="center")
    table.add_column("Name", min_width=12)
    table.add_column("Status", min_width=10)
    table.add_column("Task", ratio=1)

    mode = data.get("mode", "quick")

    # Orchestrator row (orchestrated mode only)
    if mode == "orchestrated":
        orch_status = data.get("orchestrator_status", "Unknown")
        orch_complete = data.get("orchestrator_complete", False)
        if orch_complete:
            orch_status = "Complete"
        icon = STATUS_ICONS.get(orch_status, "?")
        style = STATUS_STYLES.get(orch_status, "")
        table.add_row(icon, "[bold magenta]Orchestrator[/bold magenta]", f"[{style}]{orch_status}[/{style}]", "[dim]Pane 0[/dim]")
        table.add_section()

    # Worker rows
    for worker in data.get("workers", []):
        status = worker.get("status", "Unknown")
        icon = STATUS_ICONS.get(status, "?")
        style = STATUS_STYLES.get(status, "")
        name = worker.get("name", f"Worker {worker.get('id', '?')}")
        task = worker.get("task", "")
        summary = worker.get("summary", "")

        task_display = task if task else "[dim]No task assigned[/dim]"
        if status == "Complete" and summary:
            task_display = f"[green]{summary}[/green]"

        table.add_row(icon, name, f"[{style}]{status}[/{style}]", task_display)

    return table


def build_progress_panel(data: dict) -> Panel:
    """Build the progress summary panel."""
    completed = data.get("completed", 0)
    total = data.get("worker_count", 0)
    running = data.get("running", 0)
    idle = data.get("idle", 0)
    orch_complete = data.get("orchestrator_complete", False)

    bar = build_progress_bar(completed, total, 30)

    text = Text()
    text.append(f"  {bar}  ", style="bold")
    text.append(f"{completed}/{total}", style="bold green")
    text.append(" complete", style="dim")

    if running > 0:
        text.append(f"  │  ", style="dim")
        text.append(f"{running}", style="bold yellow")
        text.append(" running", style="dim")

    if idle > 0:
        text.append(f"  │  ", style="dim")
        text.append(f"{idle}", style="dim")
        text.append(" idle", style="dim")

    if orch_complete:
        text.append("\n\n  ", style="")
        text.append("✔ ORCHESTRATION COMPLETE", style="bold green")
        text.append(" — Final report: queue/reports/orchestrator_report.md", style="dim")
    elif completed == total and total > 0:
        text.append("\n\n  ", style="")
        text.append("⟳ All workers done, waiting for orchestrator...", style="bold yellow")

    return Panel(text, title="[bold]Progress[/bold]", border_style="green" if orch_complete else "yellow")


def build_report_panel(work_dir: str) -> Panel:
    """Build a panel showing the final report if it exists."""
    report_path = Path(work_dir) / "queue" / "reports" / "orchestrator_report.md"
    if report_path.exists():
        content = read_file_preview(report_path, max_lines=15)
        return Panel(content, title="[bold green]Final Report[/bold green]", border_style="green")
    return Panel("[dim]Waiting for orchestrator to write final report...[/dim]", title="[bold]Final Report[/bold]", border_style="dim")


def build_dashboard(data: dict | None, work_dir: str) -> Layout:
    """Compose the full dashboard layout."""
    layout = Layout()

    if data is None:
        layout.update(Panel(
            "[bold red]Cannot connect to check-status.sh[/bold red]\n\n"
            "Ensure the script exists at:\n"
            f"  {CHECK_STATUS_SH}\n\n"
            "And run this monitor from the project working directory,\n"
            "or pass the working directory as the 3rd argument.",
            title="Error",
            border_style="red",
        ))
        return layout

    orch_complete = data.get("orchestrator_complete", False)

    layout.split_column(
        Layout(name="header", size=5 if data.get("goal") else 4),
        Layout(name="body"),
        Layout(name="progress", size=5 if not orch_complete else 6),
    )

    layout["header"].update(build_header(data))
    layout["progress"].update(build_progress_panel(data))

    if orch_complete:
        layout["body"].split_column(
            Layout(name="table", ratio=1),
            Layout(name="report", ratio=1),
        )
        layout["body"]["table"].update(Panel(build_workers_table(data), title="[bold]Workers[/bold]", border_style="blue"))
        layout["body"]["report"].update(build_report_panel(work_dir))
    else:
        layout["body"].update(Panel(build_workers_table(data), title="[bold]Workers[/bold]", border_style="blue"))

    return layout


def main() -> None:
    session = sys.argv[1] if len(sys.argv) > 1 else "orchestration"
    worker_count = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    work_dir = sys.argv[3] if len(sys.argv) > 3 else "."

    console = Console()

    console.print(f"\n[bold cyan]tmux-orchestrating Monitor[/bold cyan]")
    console.print(f"[dim]Session: {session} | Workers: {worker_count} | Dir: {work_dir}[/dim]")
    console.print(f"[dim]Refresh: {REFRESH_INTERVAL}s | Press Ctrl+C to exit[/dim]\n")

    try:
        with Live(console=console, refresh_per_second=1, screen=True) as live:
            while True:
                data = get_status(session, worker_count, work_dir)
                dashboard = build_dashboard(data, work_dir)
                live.update(dashboard)
                time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        console.print("\n[dim]Monitor stopped.[/dim]")


if __name__ == "__main__":
    main()
