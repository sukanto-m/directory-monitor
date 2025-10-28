# Agentic RAG Directory Monitor - Setup Guide

## Installation

### 1. Install Ollama (for local LLM)

**macOS/Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from https://ollama.com/download

### 2. Pull LLM Models

```bash
# Qwen (recommended for coding/analysis)
ollama pull qwen2.5:latest

# Or Llama
ollama pull llama3.2:latest

# Smaller/faster option
ollama pull qwen2.5:7b
```

### 3. Install Python Dependencies

```bash
pip install ollama sentence-transformers numpy
```

**requirements.txt:**
```
ollama>=0.1.0
sentence-transformers>=2.2.0
numpy>=1.24.0
```

## Configuration

### Customize Standards

Edit the `DevelopmentStandards.STANDARDS` dict:

```python
STANDARDS = {
    "max_depth": 5,  # Your preferred max depth
    "max_files_per_dir": 20,
    "forbidden_patterns": [
        # Add your team's forbidden patterns
        "Untitled", "temp", "backup"
    ],
    "recommended_structure": [
        # Your project structure
        "src/", "tests/", "docs/"
    ]
}
```

### Watch Specific Directory

```python
monitor = AgenticMonitor(
    watch_path="/path/to/your/project",
    model_name="qwen2.5:latest"
)
```

### Adjust Monitoring Frequency

```python
CHECK_INTERVAL = 3600  # Check every hour
ALERT_THRESHOLD = 6.0   # Alert only on serious mess
```

## Usage

### Basic Monitoring

```python
from directory_monitor import AgenticMonitor

monitor = AgenticMonitor("./my_project", model_name="qwen2.5:latest")
result = monitor.scan_and_alert(alert_threshold=5.0)

if result['alert']:
    print(result['llm_analysis'])
```

### One-Time Scan

```python
from directory_monitor import DirectoryAnalyzer

analyzer = DirectoryAnalyzer("./my_project")
snapshot = analyzer.scan_directory()

print(f"Files: {snapshot.total_files}")
print(f"Violations: {len(snapshot.naming_violations)}")
```

### Custom Ignore Patterns

```python
snapshot = analyzer.scan_directory(
    ignore_patterns=['.git', '__pycache__', 'node_modules', 'dist', 'build']
)
```

## Notifications

### Email Alerts

Add to `scan_and_alert`:

```python
if analysis['alert']:
    import smtplib
    from email.message import EmailMessage
    
    msg = EmailMessage()
    msg['Subject'] = '🚨 Directory Alert'
    msg['From'] = 'monitor@yourdomain.com'
    msg['To'] = 'you@yourdomain.com'
    msg.set_content(analysis['llm_analysis'])
    
    with smtplib.SMTP('localhost') as s:
        s.send_message(msg)
```

### Slack Webhook

```python
import requests

if analysis['alert']:
    webhook_url = "YOUR_SLACK_WEBHOOK_URL"
    requests.post(webhook_url, json={
        "text": f"🚨 Directory Alert\n{analysis['llm_analysis']}"
    })
```

## Advanced Features

### 1. Historical Trend Analysis

```python
# Track messiness over time
scores = [h['messiness_score'] for h in monitor.history]
avg_score = sum(scores) / len(scores)
print(f"Average messiness: {avg_score:.1f}")
```

### 2. Export Reports

```python
import json

with open('directory_report.json', 'w') as f:
    json.dump(monitor.history, f, indent=2)
```

### 3. Custom RAG Queries

```python
# Ask LLM about specific patterns
results = monitor.vector_store.search("directories with too many files", top_k=5)
for r in results:
    print(r['snapshot']['timestamp'])
```

## Model Selection Guide

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| qwen2.5:7b | 4.7GB | Fast | Good | Quick checks |
| qwen2.5:latest | 8-14GB | Medium | Excellent | Detailed analysis |
| llama3.2:latest | 7-8GB | Medium | Very Good | General purpose |
| codellama:latest | 7-13GB | Medium | Great | Code-focused |

## Troubleshooting

### Ollama Connection Issues

```python
# Test connection
import ollama
try:
    ollama.list()
    print("✓ Ollama connected")
except:
    print("✗ Start ollama: ollama serve")
```

### Memory Issues

```python
# Use smaller model
monitor = AgenticMonitor("./", model_name="qwen2.5:7b")

# Or disable embeddings
EMBEDDINGS_AVAILABLE = False
```

### Rate Limiting

```python
# Add delay between LLM calls
import time
time.sleep(1)  # Wait 1s between calls
```

## Example Output

```
🤖 Agentic RAG Directory Monitor
==================================================

Watching: ./my_project
Model: qwen2.5:latest
Alert Threshold: 5.0/10
Check Interval: 300s

[2025-10-27 10:30:45] Scanning directory...

🚨 ALERT: Directory messiness score is 6.5/10

LLM Analysis:
Yes, this directory structure is messy.

Top 3 Issues:
1. Excessive naming violations (12 files with "temp", "backup" in names)
2. Directory depth exceeds 7 levels (recommended: 5)
3. 3 files over 100MB without clear organization

Recommended Actions:
1. Move temp/backup files to dedicated .archive/ folder
2. Flatten nested directories under src/components/
3. Move large data files to data/ directory
4. Standardize naming: use kebab-case without spaces

Messiness Rating: 7/10 - Requires immediate attention

⚠️  Consider cleaning up your directory structure!

Next scan in 300s...
```

## Scheduling

### Cron (Linux/Mac)

```bash
# Run every hour
0 * * * * cd /path/to/project && python directory_monitor.py >> monitor.log 2>&1
```

### systemd Service

Create `/etc/systemd/system/dirmonitor.service`:

```ini
[Unit]
Description=Directory Monitor

[Service]
ExecStart=/usr/bin/python3 /path/to/directory_monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Windows Task Scheduler

Run `taskschd.msc` and create a task that runs `python directory_monitor.py` on your schedule.
