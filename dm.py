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

# HTML Template
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
            --bg: #0a0a0a; --surface: #1a1a1a; --text: #e0e0e0;
            --accent: #00ff88; --warning: #ffaa00; --danger: #ff4444; --border: #2a2a2a;
        }
        body { font-family: -apple-system, sans-serif; background: var(--bg); color: var(--text);
               padding: 2rem; max-width: 1200px; margin: 0 auto; }
        .header { margin-bottom: 3rem; border-bottom: 1px solid var(--border); padding-bottom: 2rem; }
        .header h1 { font-size: 2rem; display: flex; align-items: center; gap: 0.75rem; }
        button { background: var(--surface); color: var(--text); border: 1px solid var(--border);
                 padding: 0.75rem 1.5rem; border-radius: 8px; cursor: pointer; }
        button.primary { background: var(--accent); color: var(--bg); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 2rem 0; }
        .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; }
        .card-value { font-size: 2rem; font-weight: 600; }
        .card-value.good { color: var(--accent); }
        .card-value.warning { color: var(--warning); }
        .card-value.danger { color: var(--danger); }
    </style>
</head>
<body>
    <div class="header">
        <h1>📁 Directory Monitor</h1>
        <p>🔒 100% Local · Private · No Cloud</p>
    </div>
    <div>
        <button class="primary" onclick="scanNow()">Scan Now</button>
        <button onclick="exportReport()">Export Report</button>
    </div>
    <div class="grid">
        <div class="card">
            <div>Messiness Score</div>
            <div class="card-value" id="score">--</div>
        </div>
        <div class="card">
            <div>Total Files</div>
            <div class="card-value" id="files">--</div>
        </div>
        <div class="card">
            <div>Violations</div>
            <div class="card-value" id="violations">--</div>
        </div>
    </div>
    <div class="card">
        <h3>Analysis</h3>
        <pre id="analysis" style="white-space: pre-wrap; color: #b0b0b0;">Run a scan to see analysis</pre>
    </div>
    <script>
        async function scanNow() {
            const res = await fetch('/api/scan', {method: 'POST'});
            const data = await res.json();
            if (data.success) {
                const r = data.result;
                document.getElementById('score').textContent = r.messiness_score.toFixed(1) + '/10';
                document.getElementById('files').textContent = r.snapshot.total_files;
                document.getElementById('violations').textContent = r.snapshot.naming_violations.length;
                document.getElementById('analysis').textContent = r.llm_analysis;
            }
        }
        async function exportReport() {
            const res = await fetch('/api/export');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'report.json';
            a.click();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/scan', methods=['POST'])
def api_scan():
    global monitor
    try:
        if monitor is None:
            monitor = AgenticMonitor('.', model_name="qwen2.5:latest")
        result = monitor.scan_and_alert(alert_threshold=5.0)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export')
def api_export():
    global monitor
    if monitor is None:
        return jsonify({'error': 'No data'}), 400
    report = {
        'generated': datetime.now().isoformat(),
        'statistics': monitor.get_statistics(),
        'history': monitor.get_history(50)
    }
    return jsonify(report)

def run_ui(host='127.0.0.1', port=5000):
    global monitor
    print("\n🎨 Directory Monitor Web UI")
    print(f"✓ Server: http://{host}:{port}\n")
    monitor = AgenticMonitor('.', model_name="qwen2.5:latest")
    app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    run_ui()
