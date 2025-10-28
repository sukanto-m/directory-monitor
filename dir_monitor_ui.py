"""
Minimalist Web UI for Directory Monitor
Local-only Flask server with clean, modern interface
"""

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import threading
import time
from datetime import datetime
from pathlib import Path
import json

# Import your monitor
from directory_monitor import AgenticMonitor, DevelopmentStandards

app = Flask(__name__)
CORS(app)

# Global monitor instance
monitor = None
monitoring_active = False
monitoring_thread = None

# HTML Template - Minimalist Design
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Directory Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg: #0a0a0a; --surface: #1a1a1a; --surface-hover: #252525;
            --text: #e0e0e0; --text-dim: #888; --accent: #00ff88;
            --accent-dim: #00cc6a; --warning: #ffaa00; --danger: #ff4444;
            --border: #2a2a2a;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg); color: var(--text); line-height: 1.6;
            padding: 2rem; max-width: 1200px; margin: 0 auto;
        }
        
        .header { 
            margin-bottom: 3rem; border-bottom: 1px solid var(--border); 
            padding-bottom: 2rem; 
        }
        
        .header h1 { 
            font-size: 2rem; font-weight: 600; margin-bottom: 0.5rem; 
            display: flex; align-items: center; gap: 0.75rem; 
        }
        
        .status-indicator { 
            width: 12px; height: 12px; border-radius: 50%; 
            background: var(--text-dim); animation: pulse 2s ease-in-out infinite; 
        }
        
        .status-indicator.active { background: var(--accent); }
        
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        
        .subtitle { color: var(--text-dim); font-size: 0.95rem; }
        
        .controls { 
            display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; 
        }
        
        button {
            background: var(--surface); color: var(--text); 
            border: 1px solid var(--border);
            padding: 0.75rem 1.5rem; border-radius: 8px; 
            font-size: 0.9rem; cursor: pointer; 
            transition: all 0.2s; font-weight: 500;
        }
        
        button:hover { 
            background: var(--surface-hover); 
            border-color: var(--accent); 
        }
        
        button.primary { 
            background: var(--accent); 
            color: var(--bg); 
            border-color: var(--accent); 
        }
        
        button.primary:hover { 
            background: var(--accent-dim); 
            border-color: var(--accent-dim); 
        }
        
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 1rem; margin-bottom: 2rem; 
        }
        
        .card { 
            background: var(--surface); border: 1px solid var(--border); 
            border-radius: 12px; padding: 1.5rem; 
            transition: border-color 0.2s; 
        }
        
        .card:hover { border-color: var(--accent); }
        
        .card-title { 
            color: var(--text-dim); font-size: 0.85rem; 
            font-weight: 500; text-transform: uppercase; 
            letter-spacing: 0.05em; margin-bottom: 0.5rem; 
        }
        
        .card-value { font-size: 2rem; font-weight: 600; margin-bottom: 0.25rem; }
        .card-value.good { color: var(--accent); }
        .card-value.warning { color: var(--warning); }
        .card-value.danger { color: var(--danger); }
        
        .messiness-bar { 
            width: 100%; height: 8px; background: var(--border); 
            border-radius: 4px; overflow: hidden; margin-top: 0.5rem; 
        }
        
        .messiness-fill { 
            height: 100%; border-radius: 4px; 
            transition: width 0.5s ease, background 0.3s; 
        }
        
        .section { margin-bottom: 2rem; }
        
        .section-title { 
            font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem; 
            display: flex; align-items: center; gap: 0.5rem; 
        }
        
        .analysis-box {
            background: var(--surface); border: 1px solid var(--border); 
            border-radius: 12px; padding: 1.5rem; 
            white-space: pre-wrap; 
            font-family: 'SF Mono', 'Monaco', monospace;
            font-size: 0.9rem; line-height: 1.8; 
            color: var(--text-dim); max-height: 400px; overflow-y: auto;
        }
        
        .history-item { 
            background: var(--surface); border: 1px solid var(--border); 
            border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; 
            transition: all 0.2s; 
        }
        
        .history-item:hover { 
            border-color: var(--accent); transform: translateX(4px); 
        }
        
        .history-header { 
            display: flex; justify-content: space-between; 
            align-items: center; margin-bottom: 0.5rem; 
        }
        
        .history-time { color: var(--text-dim); font-size: 0.85rem; }
        .history-score { 
            font-weight: 600; padding: 0.25rem 0.75rem; 
            border-radius: 6px; font-size: 0.85rem; 
        }
        
        .alert-badge { 
            display: inline-block; padding: 0.25rem 0.75rem; 
            border-radius: 6px; font-size: 0.75rem; font-weight: 600; 
            text-transform: uppercase; letter-spacing: 0.05em; 
        }
        
        .alert-badge.active { background: var(--danger); color: white; }
        .alert-badge.clean { background: var(--accent); color: var(--bg); }
        
        .empty-state { 
            text-align: center; padding: 3rem 1rem; color: var(--text-dim); 
        }
        
        .empty-state svg { 
            width: 64px; height: 64px; margin-bottom: 1rem; opacity: 0.3; 
        }
        
        .loader { 
            display: inline-block; width: 16px; height: 16px; 
            border: 2px solid var(--border); border-top-color: var(--accent); 
            border-radius: 50%; animation: spin 0.8s linear infinite; 
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: var(--surface); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--accent); }
        
        @media (max-width: 768px) {
            body { padding: 1rem; }
            .grid { grid-template-columns: 1fr; }
            .controls { flex-direction: column; }
            button { width: 100%; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>
            <span class="status-indicator" id="statusIndicator"></span>
            Directory Monitor
        </h1>
        <p class="subtitle">🔒 100% Local · Private · No Cloud</p>
    </div>
    
    <div class="controls">
        <button class="primary" onclick="scanNow()" id="scanBtn">
            <span id="scanBtnText">Scan Now</span>
        </button>
        <button onclick="toggleMonitoring()" id="monitorBtn">Start Monitoring</button>
        <button onclick="exportReport()">Export Report</button>
        <button onclick="refreshData()">Refresh</button>
    </div>
    
    <div class="grid">
        <div class="card">
            <div class="card-title">Messiness Score</div>
            <div class="card-value" id="messinessScore">--</div>
            <div class="messiness-bar">
                <div class="messiness-fill" id="messinessFill"></div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-title">Total Files</div>
            <div class="card-value" id="totalFiles">--</div>
        </div>
        
        <div class="card">
            <div class="card-title">Violations</div>
            <div class="card-value" id="violations">--</div>
        </div>
        
        <div class="card">
            <div class="card-title">Total Scans</div>
            <div class="card-value good" id="totalScans">--</div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-title">
            Latest Analysis
            <span id="analysisTime" class="history-time"></span>
        </div>
        <div class="analysis-box" id="analysisBox">
            <div class="empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                    <polyline points="13 2 13 9 20 9"></polyline>
                </svg>
                <p>Run a scan to see analysis</p>
            </div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-title">Recent History</div>
        <div id="historyList">
            <div class="empty-state">
                <p>No scan history yet</p>
            </div>
        </div>
    </div>
    
    <script>
        let monitoringActive = false;
        
        async function scanNow() {
            const btn = document.getElementById('scanBtn');
            const btnText = document.getElementById('scanBtnText');
            
            btn.disabled = true;
            btnText.innerHTML = '<span class="loader"></span> Scanning...';
            
            try {
                const response = await fetch('/api/scan', { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    updateUI(data.result);
                    await loadHistory();
                    await loadStats();
                } else {
                    console.error('Scan failed:', data.error);
                    alert('Scan failed: ' + data.error);
                }
            } catch (error) {
                console.error('Scan failed:', error);
                alert('Scan failed. Check console for details.');
            }
            
            btn.disabled = false;
            btnText.textContent = 'Scan Now';
        }
        
        async function toggleMonitoring() {
            const btn = document.getElementById('monitorBtn');
            
            try {
                const action = monitoringActive ? 'stop' : 'start';
                const response = await fetch(`/api/monitor/${action}`, { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    monitoringActive = !monitoringActive;
                    btn.textContent = monitoringActive ? 'Stop Monitoring' : 'Start Monitoring';
                    updateStatusIndicator(monitoringActive);
                }
            } catch (error) {
                console.error('Failed to toggle monitoring:', error);
            }
        }
        
        async function exportReport() {
            try {
                const response = await fetch('/api/export');
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `monitor-report-${Date.now()}.json`;
                a.click();
            } catch (error) {
                console.error('Export failed:', error);
            }
        }
        
        async function loadHistory() {
            try {
                const response = await fetch('/api/history');
                const data = await response.json();
                
                const historyList = document.getElementById('historyList');
                
                if (!data.history || data.history.length === 0) {
                    historyList.innerHTML = '<div class="empty-state"><p>No scan history yet</p></div>';
                    return;
                }
                
                historyList.innerHTML = data.history.map(item => `
                    <div class="history-item">
                        <div class="history-header">
                            <span class="history-time">${new Date(item.timestamp).toLocaleString()}</span>
                            <span class="history-score ${getScoreClass(item.messiness_score)}">${item.messiness_score.toFixed(1)}/10</span>
                        </div>
                        <span class="alert-badge ${item.alert ? 'active' : 'clean'}">
                            ${item.alert ? '🚨 Alert' : '✓ Clean'}
                        </span>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Failed to load history:', error);
            }
        }
        
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                if (data.stats) {
                    document.getElementById('totalScans').textContent = data.stats.total_scans || 0;
                }
            } catch (error) {
                console.error('Failed to load stats:', error);
            }
        }
        
        function updateUI(result) {
            // Update messiness score
            const score = result.messiness_score;
            const scoreEl = document.getElementById('messinessScore');
            scoreEl.textContent = `${score.toFixed(1)}/10`;
            scoreEl.className = `card-value ${getScoreClass(score)}`;
            
            // Update messiness bar
            const fill = document.getElementById('messinessFill');
            fill.style.width = `${(score / 10) * 100}%`;
            fill.style.background = getScoreColor(score);
            
            // Update other metrics
            document.getElementById('totalFiles').textContent = result.snapshot.total_files || 0;
            document.getElementById('violations').textContent = result.snapshot.naming_violations.length || 0;
            
            // Update analysis
            document.getElementById('analysisBox').textContent = result.llm_analysis || 'No analysis available';
            document.getElementById('analysisTime').textContent = new Date(result.timestamp).toLocaleString();
        }
        
        function getScoreClass(score) {
            if (score < 3) return 'good';
            if (score < 7) return 'warning';
            return 'danger';
        }
        
        function getScoreColor(score) {
            if (score < 3) return 'var(--accent)';
            if (score < 7) return 'var(--warning)';
            return 'var(--danger)';
        }
        
        function updateStatusIndicator(active) {
            const indicator = document.getElementById('statusIndicator');
            if (active) {
                indicator.classList.add('active');
            } else {
                indicator.classList.remove('active');
            }
        }
        
        async function refreshData() {
            await loadHistory();
            await loadStats();
        }
        
        // Load initial data
        window.addEventListener('DOMContentLoaded', () => {
            refreshData();
            // Auto-refresh every 30 seconds
            setInterval(refreshData, 30000);
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main UI"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/scan', methods=['POST'])
def api_scan():
    """Trigger a single scan"""
    global monitor
    
    try:
        if monitor is None:
            watch_path = request.json.get('path', '.') if request.json else '.'
            monitor = AgenticMonitor(watch_path, model_name="qwen3:8b")
        
        result = monitor.scan_and_alert(alert_threshold=5.0)
        
        return jsonify({
            'success': True,
            'result': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/monitor/start', methods=['POST'])
def api_monitor_start():
    """Start continuous monitoring"""
    global monitoring_active, monitoring_thread, monitor
    
    if monitoring_active:
        return jsonify({'success': False, 'error': 'Already monitoring'})
    
    if monitor is None:
        watch_path = request.json.get('path', '.') if request.json else '.'
        monitor = AgenticMonitor(watch_path, model_name="qwen3:8b")
    
    monitoring_active = True
    
    def monitor_loop():
        while monitoring_active:
            try:
                monitor.scan_and_alert(alert_threshold=5.0)
                time.sleep(300)  # 5 minutes
            except Exception as e:
                print(f"Monitoring error: {e}")
                break
    
    monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitoring_thread.start()
    
    return jsonify({'success': True})

@app.route('/api/monitor/stop', methods=['POST'])
def api_monitor_stop():
    """Stop continuous monitoring"""
    global monitoring_active
    
    monitoring_active = False
    
    return jsonify({'success': True})

@app.route('/api/history')
def api_history():
    """Get scan history"""
    global monitor
    
    if monitor is None:
        return jsonify({'history': []})
    
    try:
        history = monitor.get_history(limit=10)
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'history': [], 'error': str(e)})

@app.route('/api/stats')
def api_stats():
    """Get statistics"""
    global monitor
    
    if monitor is None:
        return jsonify({'stats': {'total_scans': 0, 'avg_messiness': 0}})
    
    try:
        stats = monitor.get_statistics()
        return jsonify({'stats': stats})
    except Exception as e:
        return jsonify({'stats': {'total_scans': 0, 'avg_messiness': 0}, 'error': str(e)})

@app.route('/api/export')
def api_export():
    """Export report as JSON"""
    global monitor
    
    if monitor is None:
        return jsonify({'error': 'No monitor initialized'}), 400
    
    try:
        report = {
            'generated': datetime.now().isoformat(),
            'statistics': monitor.get_statistics(),
            'history': monitor.get_history(50)
        }
        
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_ui(host='127.0.0.1', port=5000, watch_path='.', model_name='qwen3:8b'):
    """Run the web UI server"""
    global monitor
    
    print("\n🎨 Starting Minimalist Directory Monitor UI")
    print("=" * 60)
    print(f"✓ Watching: {Path(watch_path).absolute()}")
    print(f"✓ Model: {model_name}")
    print(f"✓ Server: http://{host}:{port}")
    print("\n🔒 All processing happens locally on your machine")
    print("   No data is sent to any external servers\n")
    
    # Initialize monitor
    monitor = AgenticMonitor(watch_path, model_name=model_name)
    
    print("Opening web interface...")
    
    # Auto-open browser (optional)
    import webbrowser
    threading.Timer(1.5, lambda: webbrowser.open(f'http://{host}:{port}')).start()
    
    # Run Flask app
    app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Directory Monitor Web UI')
    parser.add_argument('--path', default='.', help='Directory to watch')
    parser.add_argument('--model', default='qwen3:8b', help='LLM model name')
    parser.add_argument('--host', default='127.0.0.1', help='Server host')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    
    args = parser.parse_args()
    
    run_ui(
        host=args.host,
        port=args.port,
        watch_path=args.path,
        model_name=args.model
    )
