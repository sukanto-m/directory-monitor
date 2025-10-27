# 🔒 Local Directory Monitor

100% local, privacy-focused directory monitoring system using AI.

## Features

- 🤖 Local LLM analysis (Qwen/Llama via Ollama)
- 📊 Beautiful Terminal UI with Rich
- 🌐 Minimalist Web UI
- 📈 Trend analysis with sparklines
- 🔒 100% private - no cloud APIs
- 💾 Local SQLite database
- 🎯 RAG with local embeddings

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull qwen2.5:latest

# Run Terminal UI
python monitor_tui.py

# Or Web UI
python monitor_ui.py
```

## Files

- `directory_monitor.py` - Core monitoring engine
- `monitor_tui.py` - Terminal interface
- `monitor_ui.py` - Web interface
- `trend_graphs.py` - Trend analysis

## Usage
```bash
# Terminal UI
python monitor_tui.py --path /your/project --model qwen3:8b

# Web UI
python monitor_ui.py --port 5000

# View trends
python trend_graphs.py --days 30
```

## Requirements

- Python 3.9+
- Ollama (for local LLM)
- 8GB+ RAM recommended

## License

MIT
