"""
Terminal UI (TUI) for Directory Monitor
Beautiful, interactive terminal interface using Rich
"""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.align import Align
from rich.columns import Columns
from rich import box
from rich.markdown import Markdown
import threading
import time
from datetime import datetime
from pathlib import Path
import sys

# Import your monitor
from directory_monitor import AgenticMonitor, DevelopmentStandards

console = Console()


class DirectoryMonitorTUI:
    """Terminal UI for Directory Monitor"""
    
    def __init__(self, watch_path: str = ".", model_name: str = "qwen2.5:latest"):
        self.watch_path = Path(watch_path).absolute()
        self.model_name = model_name
        self.monitor = None
        self.monitoring_active = False
        self.current_result = None
        self.last_scan_time = None
        self.scan_count = 0
        
        # Initialize monitor
        console.print("\n[cyan]🔧 Initializing local monitor...[/cyan]")
        self.monitor = AgenticMonitor(str(watch_path), model_name=model_name)
        console.print("[green]✓ Monitor ready[/green]\n")
        
    def create_header(self) -> Panel:
        """Create header panel"""
        status = "🟢 ACTIVE" if self.monitoring_active else "⚪ IDLE"
        
        header_text = Text()
        header_text.append("Directory Monitor", style="bold cyan")
        header_text.append(" | ", style="dim")
        header_text.append(status, style="bold green" if self.monitoring_active else "dim")
        header_text.append(" | ", style="dim")
        header_text.append("🔒 100% Local", style="bold magenta")
        
        return Panel(
            Align.center(header_text),
            style="cyan",
            box=box.DOUBLE
        )
    
    def create_info_panel(self) -> Panel:
        """Create info panel with path and model"""
        info = Table.grid(padding=(0, 2))
        info.add_column(style="cyan", justify="right")
        info.add_column(style="white")
        
        info.add_row("Watching:", str(self.watch_path))
        info.add_row("Model:", self.model_name)
        info.add_row("Scans:", str(self.scan_count))
        
        if self.last_scan_time:
            info.add_row("Last Scan:", self.last_scan_time.strftime("%H:%M:%S"))
        
        return Panel(info, title="[bold]Configuration[/bold]", border_style="blue")
    
    def create_metrics_panel(self) -> Panel:
        """Create metrics panel with cards"""
        if not self.current_result:
            return Panel(
                Align.center("[dim]Run a scan to see metrics[/dim]"),
                title="[bold]Metrics[/bold]",
                border_style="blue"
            )
        
        snapshot = self.current_result['snapshot']
        score = self.current_result['messiness_score']
        
        # Determine score color
        if score < 3:
            score_color = "green"
            score_emoji = "✅"
        elif score < 7:
            score_color = "yellow"
            score_emoji = "⚠️"
        else:
            score_color = "red"
            score_emoji = "🚨"
        
        # Create metric cards
        metrics = Table.grid(padding=(0, 2))
        metrics.add_column(justify="center")
        metrics.add_column(justify="center")
        metrics.add_column(justify="center")
        metrics.add_column(justify="center")
        
        # Messiness Score
        score_panel = Panel(
            Align.center(
                Text(f"{score_emoji}\n{score:.1f}/10", style=f"bold {score_color}", justify="center")
            ),
            title="Messiness",
            border_style=score_color,
            width=18
        )
        
        # Total Files
        files_panel = Panel(
            Align.center(
                Text(f"📄\n{snapshot['total_files']}", style="bold cyan", justify="center")
            ),
            title="Files",
            border_style="cyan",
            width=18
        )
        
        # Violations
        violations = len(snapshot['naming_violations'])
        viol_color = "red" if violations > 5 else "yellow" if violations > 0 else "green"
        violations_panel = Panel(
            Align.center(
                Text(f"⚡\n{violations}", style=f"bold {viol_color}", justify="center")
            ),
            title="Violations",
            border_style=viol_color,
            width=18
        )
        
        # Directories
        dirs_panel = Panel(
            Align.center(
                Text(f"📁\n{snapshot['total_dirs']}", style="bold magenta", justify="center")
            ),
            title="Dirs",
            border_style="magenta",
            width=18
        )
        
        metrics.add_row(score_panel, files_panel, violations_panel, dirs_panel)
        
        return Panel(metrics, title="[bold]Metrics[/bold]", border_style="blue")
    
    def create_analysis_panel(self) -> Panel:
        """Create LLM analysis panel"""
        if not self.current_result:
            return Panel(
                Align.center("[dim]No analysis yet[/dim]"),
                title="[bold]LLM Analysis[/bold]",
                border_style="green"
            )
        
        analysis = self.current_result.get('llm_analysis', 'No analysis available')
        
        # Truncate if too long
        max_lines = 15
        lines = analysis.split('\n')
        if len(lines) > max_lines:
            analysis = '\n'.join(lines[:max_lines]) + '\n\n[dim]...[truncated][/dim]'
        
        return Panel(
            analysis,
            title="[bold]LLM Analysis[/bold]",
            border_style="green",
            padding=(1, 2)
        )
    
    def create_violations_panel(self) -> Panel:
        """Create violations panel"""
        if not self.current_result:
            return Panel(
                Align.center("[dim]No violations yet[/dim]"),
                title="[bold]Issues[/bold]",
                border_style="yellow"
            )
        
        violations = self.current_result['snapshot']['naming_violations']
        
        if not violations:
            return Panel(
                Align.center("✅ [green]No issues found![/green]"),
                title="[bold]Issues[/bold]",
                border_style="green"
            )
        
        # Create table
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        table.add_column("Issue", style="yellow")
        
        for v in violations[:10]:  # Show first 10
            table.add_row(f"⚠️  {v}")
        
        if len(violations) > 10:
            table.add_row(f"[dim]... and {len(violations) - 10} more[/dim]")
        
        return Panel(table, title=f"[bold]Issues ({len(violations)})[/bold]", border_style="yellow")
    
    def create_trend_panel(self) -> Panel:
        """Create trend sparkline panel"""
        try:
            # Import trend analyzer
            import sqlite3
            from collections import defaultdict
            
            # Get last 30 data points
            conn = sqlite3.connect(self.monitor.db.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT messiness_score
                FROM snapshots
                ORDER BY timestamp DESC
                LIMIT 30
            """)
            scores = [row[0] for row in cursor.fetchall()]
            scores.reverse()  # Oldest to newest
            conn.close()
            
            if not scores or len(scores) < 2:
                return Panel(
                    Align.center("[dim]Need more scans for trends[/dim]"),
                    title="[bold]Trend (Last 30 Scans)[/bold]",
                    border_style="cyan"
                )
            
            # Generate sparkline
            sparkline = self._generate_sparkline(scores, width=50)
            
            # Calculate trend
            recent_avg = sum(scores[-7:]) / min(len(scores), 7)
            older_avg = sum(scores[:-7]) / max(len(scores) - 7, 1) if len(scores) > 7 else recent_avg
            
            if recent_avg < older_avg - 0.5:
                trend = "📉 Improving"
                trend_color = "green"
            elif recent_avg > older_avg + 0.5:
                trend = "📈 Worsening"
                trend_color = "red"
            else:
                trend = "➡️  Stable"
                trend_color = "yellow"
            
            content = Text()
            content.append(sparkline + "\n\n", style="green")
            content.append(f"Min: {min(scores):.1f}  ", style="green")
            content.append(f"Avg: {sum(scores)/len(scores):.1f}  ", style="yellow")
            content.append(f"Max: {max(scores):.1f}\n", style="red")
            content.append(f"Trend: ", style="dim")
            content.append(trend, style=trend_color)
            
            return Panel(
                content,
                title="[bold]Trend (Last 30 Scans)[/bold]",
                border_style="cyan"
            )
        
        except Exception as e:
            return Panel(
                Align.center(f"[dim]Trend unavailable[/dim]"),
                title="[bold]Trend[/bold]",
                border_style="cyan"
            )
    
    def _generate_sparkline(self, data: list, width: int = 50) -> str:
        """Generate ASCII sparkline"""
        if not data:
            return ""
        
        # Normalize data
        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val if max_val != min_val else 1
        
        # Scale to 8 levels
        scaled = [int((v - min_val) / range_val * 7) for v in data]
        
        # Sample data to fit width
        if len(scaled) > width:
            step = len(scaled) / width
            scaled = [scaled[int(i * step)] for i in range(width)]
        
        # Build sparkline
        chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
        return ''.join(chars[min(h, 7)] for h in scaled)
    
    def create_history_panel(self) -> Panel:
        """Create history panel"""
        if not self.monitor:
            return Panel(
                Align.center("[dim]No history yet[/dim]"),
                title="[bold]Recent History[/bold]",
                border_style="magenta"
            )
        
        history = self.monitor.get_history(limit=5)
        
        if not history:
            return Panel(
                Align.center("[dim]No scans yet[/dim]"),
                title="[bold]Recent History[/bold]",
                border_style="magenta"
            )
        
        table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
        table.add_column("Time", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Status", justify="center")
        
        for h in history:
            timestamp = datetime.fromisoformat(h['timestamp']).strftime("%H:%M:%S")
            score = f"{h['messiness_score']:.1f}/10"
            
            if h['messiness_score'] < 3:
                score_style = "green"
                status = "✅"
            elif h['messiness_score'] < 7:
                score_style = "yellow"
                status = "⚠️"
            else:
                score_style = "red"
                status = "🚨"
            
            table.add_row(
                timestamp,
                f"[{score_style}]{score}[/{score_style}]",
                status
            )
        
        return Panel(table, title="[bold]Recent History[/bold]", border_style="magenta")
    
    def create_help_panel(self) -> Panel:
        """Create help panel with keyboard shortcuts"""
        help_text = Table.grid(padding=(0, 2))
        help_text.add_column(style="cyan bold")
        help_text.add_column(style="white")
        
        help_text.add_row("S", "Scan now")
        help_text.add_row("M", "Toggle monitoring")
        help_text.add_row("E", "Export report")
        help_text.add_row("R", "Refresh view")
        help_text.add_row("Q", "Quit")
        
        return Panel(
            help_text,
            title="[bold]Controls[/bold]",
            border_style="cyan"
        )
    
    def create_layout(self) -> Layout:
        """Create main layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=9)
        )
        
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split_column(
            Layout(name="info", size=8),
            Layout(name="metrics", size=10),
            Layout(name="violations")
        )
        
        layout["right"].split_column(
            Layout(name="analysis"),
            Layout(name="trend", size=10),
            Layout(name="history", size=12)
        )
        
        layout["footer"].split_row(
            Layout(name="help", ratio=1),
            Layout(name="stats", ratio=2)
        )
        
        return layout
    
    def update_layout(self, layout: Layout):
        """Update layout with current data"""
        layout["header"].update(self.create_header())
        layout["info"].update(self.create_info_panel())
        layout["metrics"].update(self.create_metrics_panel())
        layout["analysis"].update(self.create_analysis_panel())
        layout["violations"].update(self.create_violations_panel())
        layout["trend"].update(self.create_trend_panel())
        layout["history"].update(self.create_history_panel())
        layout["help"].update(self.create_help_panel())
        
        # Stats panel
        if self.monitor:
            stats = self.monitor.get_statistics()
            stats_text = Table.grid(padding=(0, 2))
            stats_text.add_column(style="cyan", justify="right")
            stats_text.add_column(style="white")
            
            stats_text.add_row("Total Scans:", str(stats['total_scans']))
            stats_text.add_row("Avg Messiness:", f"{stats['avg_messiness']:.1f}/10")
            stats_text.add_row("Max Messiness:", f"{stats['max_messiness']:.1f}/10")
            stats_text.add_row("Min Messiness:", f"{stats['min_messiness']:.1f}/10")
            
            layout["stats"].update(
                Panel(stats_text, title="[bold]Statistics[/bold]", border_style="cyan")
            )
    
    def scan(self):
        """Perform a scan"""
        console.print("\n[cyan]🔍 Scanning directory...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Analyzing...", total=100)
            
            # Simulate progress (actual scan happens instantly)
            for i in range(0, 100, 20):
                time.sleep(0.1)
                progress.update(task, advance=20)
            
            self.current_result = self.monitor.scan_and_alert(alert_threshold=5.0)
            self.last_scan_time = datetime.now()
            self.scan_count += 1
        
        # Show alert if needed
        if self.current_result['alert']:
            console.print(f"\n[bold red]🚨 ALERT: {self.current_result['message']}[/bold red]\n")
        else:
            console.print(f"\n[bold green]✅ {self.current_result['message']}[/bold green]\n")
    
    def toggle_monitoring(self):
        """Toggle continuous monitoring"""
        if self.monitoring_active:
            self.monitoring_active = False
            console.print("\n[yellow]⏸️  Monitoring paused[/yellow]\n")
        else:
            self.monitoring_active = True
            console.print("\n[green]▶️  Monitoring started[/green]\n")
            
            def monitor_loop():
                while self.monitoring_active:
                    try:
                        self.scan()
                        time.sleep(300)  # 5 minutes
                    except Exception as e:
                        console.print(f"\n[red]Error: {e}[/red]\n")
                        break
            
            thread = threading.Thread(target=monitor_loop, daemon=True)
            thread.start()
    
    def export_report(self):
        """Export report to file"""
        filename = f"monitor-report-{int(time.time())}.json"
        self.monitor.export_report(filename)
        console.print(f"\n[green]✅ Report exported: {filename}[/green]\n")
    
    def run_simple(self):
        """Run simple TUI without keyboard library"""
        layout = self.create_layout()
        
        console.clear()
        
        # Show initial view
        self.update_layout(layout)
        console.print(layout)
        
        console.print("\n[bold cyan]Interactive Commands:[/bold cyan]")
        console.print("  [cyan]s[/cyan] - Scan now")
        console.print("  [cyan]m[/cyan] - Toggle monitoring")
        console.print("  [cyan]e[/cyan] - Export report")
        console.print("  [cyan]r[/cyan] - Refresh")
        console.print("  [cyan]q[/cyan] - Quit\n")
        
        try:
            while True:
                command = input("Command: ").strip().lower()
                
                if command == 's':
                    self.scan()
                    console.clear()
                    self.update_layout(layout)
                    console.print(layout)
                
                elif command == 'm':
                    self.toggle_monitoring()
                
                elif command == 'e':
                    self.export_report()
                
                elif command == 'r':
                    console.clear()
                    self.update_layout(layout)
                    console.print(layout)
                
                elif command == 'q':
                    break
                
                else:
                    console.print("[yellow]Unknown command. Use s/m/e/r/q[/yellow]")
        
        except KeyboardInterrupt:
            pass
        
        console.print("\n[yellow]👋 Goodbye![/yellow]\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Directory Monitor TUI')
    parser.add_argument('--path', default='.', help='Directory to watch')
    parser.add_argument('--model', default='qwen2.5:latest', help='LLM model name')
    
    args = parser.parse_args()
    
    tui = DirectoryMonitorTUI(watch_path=args.path, model_name=args.model)
    tui.run_simple()


if __name__ == "__main__":
    main()
