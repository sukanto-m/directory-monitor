"""
Trend Graphs Module for Directory Monitor
Visualize messiness trends over time - all local, no cloud
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import json

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    print("Install rich: pip install rich")


class TrendAnalyzer:
    """Analyze trends from local database"""
    
    def __init__(self, db_path: str = "./directory_monitor.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
    
    def get_time_series(self, days: int = 30) -> List[Dict]:
        """Get time series data for the last N days"""
        cursor = self.conn.cursor()
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        cursor.execute("""
            SELECT timestamp, messiness_score, total_files, total_dirs
            FROM snapshots
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (cutoff_str,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'timestamp': datetime.fromisoformat(row[0]),
                'messiness_score': row[1],
                'total_files': row[2],
                'total_dirs': row[3]
            })
        return results
    
    def get_statistics_summary(self) -> Dict:
        """Get comprehensive statistics"""
        cursor = self.conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_scans,
                AVG(messiness_score) as avg_score,
                MIN(messiness_score) as min_score,
                MAX(messiness_score) as max_score,
                AVG(total_files) as avg_files,
                AVG(total_dirs) as avg_dirs
            FROM snapshots
        """)
        row = cursor.fetchone()
        
        # Recent trend
        cursor.execute("""
            SELECT AVG(messiness_score)
            FROM snapshots
            WHERE timestamp >= datetime('now', '-7 days')
        """)
        recent_avg = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT AVG(messiness_score)
            FROM snapshots
            WHERE timestamp BETWEEN datetime('now', '-14 days') AND datetime('now', '-7 days')
        """)
        previous_avg = cursor.fetchone()[0] or 0
        
        trend = "improving" if recent_avg < previous_avg else "worsening" if recent_avg > previous_avg else "stable"
        trend_delta = abs(recent_avg - previous_avg)
        
        return {
            'total_scans': row[0],
            'avg_score': round(row[1], 2) if row[1] else 0,
            'min_score': round(row[2], 2) if row[2] else 0,
            'max_score': round(row[3], 2) if row[3] else 0,
            'avg_files': int(row[4]) if row[4] else 0,
            'avg_dirs': int(row[5]) if row[5] else 0,
            'trend': trend,
            'trend_delta': round(trend_delta, 2),
            'recent_avg': round(recent_avg, 2),
            'previous_avg': round(previous_avg, 2)
        }
    
    def close(self):
        self.conn.close()


class TerminalSparkline:
    """Create ASCII sparkline graphs for terminal"""
    
    @staticmethod
    def generate(data: List[float], width: int = 50) -> str:
        """Generate ASCII sparkline"""
        if not data:
            return "No data"
        
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
        line = ''.join(chars[min(h, 7)] for h in scaled)
        return line


def show_trends_in_terminal(db_path: str = "./directory_monitor.db", days: int = 30):
    """Show trends in terminal using Rich"""
    if not RICH_AVAILABLE:
        print("Rich required. Install: pip install rich")
        return
    
    analyzer = TrendAnalyzer(db_path)
    data = analyzer.get_time_series(days)
    stats = analyzer.get_statistics_summary()
    
    if not data:
        console.print("[yellow]No data available yet. Run some scans first![/yellow]")
        return
    
    console.print("\n[bold cyan]📊 Trend Analysis[/bold cyan]\n")
    
    # Statistics summary
    stats_table = Table(title="Statistics Summary", box=box.ROUNDED, border_style="cyan")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="white", justify="right")
    
    stats_table.add_row("Total Scans", str(stats['total_scans']))
    stats_table.add_row("Average Score", f"{stats['avg_score']}/10")
    stats_table.add_row("Min Score", f"{stats['min_score']}/10")
    stats_table.add_row("Max Score", f"{stats['max_score']}/10")
    stats_table.add_row("Average Files", str(stats['avg_files']))
    stats_table.add_row("Average Dirs", str(stats['avg_dirs']))
    
    # Trend indicator
    trend_emoji = "📈" if stats['trend'] == "worsening" else "📉" if stats['trend'] == "improving" else "➡️"
    trend_color = "red" if stats['trend'] == "worsening" else "green" if stats['trend'] == "improving" else "yellow"
    stats_table.add_row(
        "7-Day Trend", 
        f"[{trend_color}]{trend_emoji} {stats['trend'].upper()} (Δ{stats['trend_delta']})[/{trend_color}]"
    )
    
    console.print(stats_table)
    console.print()
    
    # Sparkline
    scores = [d['messiness_score'] for d in data]
    sparkline = TerminalSparkline.generate(scores, width=60)
    
    console.print(Panel(
        f"[cyan]Messiness Trend (Last {days} Days)[/cyan]\n\n"
        f"[green]{sparkline}[/green]\n\n"
        f"Min: [green]{min(scores):.1f}[/green]  "
        f"Avg: [yellow]{sum(scores)/len(scores):.1f}[/yellow]  "
        f"Max: [red]{max(scores):.1f}[/red]",
        title="📈 Trend Sparkline",
        border_style="green"
    ))
    
    analyzer.close()


def main():
    """Main function for trend visualization"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Directory Monitor Trend Analysis')
    parser.add_argument('--db', default='./directory_monitor.db', help='Database path')
    parser.add_argument('--days', type=int, default=30, help='Days to analyze')
    
    args = parser.parse_args()
    
    if not Path(args.db).exists():
        print(f"❌ Database not found: {args.db}")
        print("Run some scans first to generate data!")
        return
    
    show_trends_in_terminal(args.db, args.days)


if __name__ == "__main__":
    main()