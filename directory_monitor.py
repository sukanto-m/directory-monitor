"""
Agentic RAG Directory Monitor - 100% Local & Private
All data stays on your machine - no cloud dependencies
"""

import os
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib
import pickle
from dataclasses import dataclass, asdict
from collections import defaultdict

# Local LLM Integration (Ollama or llama.cpp)
try:
    import ollama
    LLM_BACKEND = "ollama"
except ImportError:
    try:
        from llama_cpp import Llama
        LLM_BACKEND = "llama_cpp"
    except ImportError:
        LLM_BACKEND = None
        print("Install either: pip install ollama OR pip install llama-cpp-python")

# Local embeddings (no API calls)
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("Install for local embeddings: pip install sentence-transformers")


@dataclass
class DirectorySnapshot:
    """Snapshot of directory structure at a point in time"""
    timestamp: str
    path: str
    total_files: int
    total_dirs: int
    file_types: Dict[str, int]
    depth_distribution: Dict[int, int]
    naming_violations: List[str]
    structure_hash: str
    largest_files: List[Dict[str, Any]]


class LocalDatabase:
    """SQLite database for storing all monitoring data locally"""
    
    def __init__(self, db_path: str = "./directory_monitor.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()
    
    def _init_schema(self):
        """Create database tables"""
        cursor = self.conn.cursor()
        
        # Snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                path TEXT NOT NULL,
                total_files INTEGER,
                total_dirs INTEGER,
                messiness_score REAL,
                structure_hash TEXT,
                snapshot_data TEXT
            )
        """)
        
        # Analysis table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER,
                timestamp TEXT NOT NULL,
                llm_analysis TEXT,
                alert_triggered BOOLEAN,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
        """)
        
        # Embeddings table (for RAG)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER,
                embedding BLOB,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
        """)
        
        # Config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        self.conn.commit()
    
    def save_snapshot(self, snapshot: DirectorySnapshot, messiness_score: float) -> int:
        """Save snapshot to database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO snapshots (timestamp, path, total_files, total_dirs, 
                                   messiness_score, structure_hash, snapshot_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot.timestamp,
            snapshot.path,
            snapshot.total_files,
            snapshot.total_dirs,
            messiness_score,
            snapshot.structure_hash,
            json.dumps(asdict(snapshot))
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def save_analysis(self, snapshot_id: int, analysis: str, alert: bool):
        """Save LLM analysis"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO analyses (snapshot_id, timestamp, llm_analysis, alert_triggered)
            VALUES (?, ?, ?, ?)
        """, (snapshot_id, datetime.now().isoformat(), analysis, alert))
        self.conn.commit()
    
    def save_embedding(self, snapshot_id: int, embedding: np.ndarray):
        """Save embedding vector"""
        cursor = self.conn.cursor()
        embedding_bytes = pickle.dumps(embedding)
        cursor.execute("""
            INSERT INTO embeddings (snapshot_id, embedding)
            VALUES (?, ?)
        """, (snapshot_id, embedding_bytes))
        self.conn.commit()
    
    def get_all_embeddings(self) -> List[tuple]:
        """Retrieve all embeddings for similarity search"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT e.snapshot_id, e.embedding, s.snapshot_data
            FROM embeddings e
            JOIN snapshots s ON e.snapshot_id = s.id
        """)
        results = []
        for row in cursor.fetchall():
            results.append((
                row[0],
                pickle.loads(row[1]),
                json.loads(row[2])
            ))
        return results
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent analysis history"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.timestamp, s.messiness_score, a.llm_analysis, a.alert_triggered
            FROM snapshots s
            LEFT JOIN analyses a ON s.id = a.snapshot_id
            ORDER BY s.timestamp DESC
            LIMIT ?
        """, (limit,))
        
        return [{
            'timestamp': row[0],
            'messiness_score': row[1],
            'analysis': row[2],
            'alert': row[3]
        } for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Get overall statistics"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_scans,
                AVG(messiness_score) as avg_score,
                MAX(messiness_score) as max_score,
                MIN(messiness_score) as min_score
            FROM snapshots
        """)
        row = cursor.fetchone()
        return {
            'total_scans': row[0],
            'avg_messiness': round(row[1], 2) if row[1] else 0,
            'max_messiness': round(row[2], 2) if row[2] else 0,
            'min_messiness': round(row[3], 2) if row[3] else 0
        }
    
    def close(self):
        """Close database connection"""
        self.conn.close()


class DevelopmentStandards:
    """Define what constitutes a 'messy' directory - fully customizable"""
    
    STANDARDS = {
        "max_depth": 5,
        "max_files_per_dir": 20,
        "forbidden_patterns": [
            "Untitled", "New Folder", "Copy of", "- Copy",
            "temp", "tmp", "backup", "old", "~$"
        ],
        "recommended_structure": [
            "src/", "tests/", "docs/", "config/", 
            "scripts/", "data/", "assets/"
        ],
        "file_naming": {
            "no_spaces": True,
            "lowercase_preferred": True,
            "no_special_chars": ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")"]
        },
        "max_file_size_mb": 100,
        "common_clutter": [
            ".DS_Store", "Thumbs.db", "desktop.ini", 
            "*.tmp", "~$*", "*.bak", "*.swp"
        ]
    }
    
    @classmethod
    def load_from_file(cls, config_path: str = "./monitor_config.json"):
        """Load custom standards from local config file"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                custom = json.load(f)
                cls.STANDARDS.update(custom)
    
    @classmethod
    def save_to_file(cls, config_path: str = "./monitor_config.json"):
        """Save current standards to local config file"""
        with open(config_path, 'w') as f:
            json.dump(cls.STANDARDS, f, indent=2)


class DirectoryAnalyzer:
    """Analyzes directory structure - all processing local"""
    
    def __init__(self, watch_path: str):
        self.watch_path = Path(watch_path)
        self.standards = DevelopmentStandards.STANDARDS
        
    def scan_directory(self, ignore_patterns=None) -> DirectorySnapshot:
        """Scan directory and create snapshot"""
        if ignore_patterns is None:
            ignore_patterns = [
                '.git', '__pycache__', 'node_modules', '.venv', 'venv',
                'dist', 'build', '.next', '.cache', 'target'
            ]
        
        total_files = 0
        total_dirs = 0
        file_types = defaultdict(int)
        depth_distribution = defaultdict(int)
        naming_violations = []
        largest_files = []
        
        for root, dirs, files in os.walk(self.watch_path):
            dirs[:] = [d for d in dirs if d not in ignore_patterns]
            
            rel_path = Path(root).relative_to(self.watch_path)
            depth = len(rel_path.parts)
            
            total_dirs += len(dirs)
            depth_distribution[depth] += len(dirs)
            
            if len(files) > self.standards['max_files_per_dir']:
                naming_violations.append(
                    f"Too many files ({len(files)}) in {rel_path}"
                )
            
            for file in files:
                total_files += 1
                file_path = Path(root) / file
                
                ext = file_path.suffix.lower() or 'no_extension'
                file_types[ext] += 1
                
                for pattern in self.standards['forbidden_patterns']:
                    if pattern.lower() in file.lower():
                        naming_violations.append(
                            f"Naming violation '{pattern}' in {rel_path / file}"
                        )
                
                if self.standards['file_naming']['no_spaces'] and ' ' in file:
                    naming_violations.append(f"Space in filename: {rel_path / file}")
                
                try:
                    size = file_path.stat().st_size
                    size_mb = size / (1024 * 1024)
                    if size_mb > self.standards['max_file_size_mb']:
                        largest_files.append({
                            'path': str(rel_path / file),
                            'size_mb': round(size_mb, 2)
                        })
                except OSError:
                    pass
        
        largest_files.sort(key=lambda x: x['size_mb'], reverse=True)
        largest_files = largest_files[:10]
        
        structure_str = json.dumps({
            'files': total_files,
            'dirs': total_dirs,
            'types': dict(file_types)
        }, sort_keys=True)
        structure_hash = hashlib.md5(structure_str.encode()).hexdigest()
        
        return DirectorySnapshot(
            timestamp=datetime.now().isoformat(),
            path=str(self.watch_path),
            total_files=total_files,
            total_dirs=total_dirs,
            file_types=dict(file_types),
            depth_distribution=dict(depth_distribution),
            naming_violations=naming_violations[:20],
            structure_hash=structure_hash,
            largest_files=largest_files
        )


class LocalVectorStore:
    """Local vector store using sentence-transformers - no cloud APIs"""
    
    def __init__(self, db: LocalDatabase, model_name='all-MiniLM-L6-v2'):
        if not EMBEDDINGS_AVAILABLE:
            raise ImportError("Install: pip install sentence-transformers")
        
        self.db = db
        # Model runs entirely on your machine
        self.model = SentenceTransformer(model_name)
        self._load_cache()
    
    def _load_cache(self):
        """Load embeddings from local database"""
        self.cache = self.db.get_all_embeddings()
    
    def add_snapshot(self, snapshot_id: int, snapshot: DirectorySnapshot):
        """Generate and store embedding locally"""
        text = self._snapshot_to_text(snapshot)
        embedding = self.model.encode(text)
        self.db.save_embedding(snapshot_id, embedding)
        self._load_cache()  # Refresh cache
    
    def _snapshot_to_text(self, snapshot: DirectorySnapshot) -> str:
        """Convert snapshot to text"""
        violations = "\n".join(snapshot.naming_violations[:5])
        return f"""
        Directory: {snapshot.path}
        Files: {snapshot.total_files}
        Directories: {snapshot.total_dirs}
        File types: {', '.join(snapshot.file_types.keys())}
        Max depth: {max(snapshot.depth_distribution.keys()) if snapshot.depth_distribution else 0}
        Violations: {violations}
        """
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search locally stored embeddings"""
        if not self.cache:
            return []
        
        query_embedding = self.model.encode(query)
        
        results = []
        for snapshot_id, embedding, snapshot_data in self.cache:
            similarity = np.dot(embedding, query_embedding) / (
                np.linalg.norm(embedding) * np.linalg.norm(query_embedding)
            )
            results.append({
                'snapshot_id': snapshot_id,
                'similarity': similarity,
                'snapshot': snapshot_data
            })
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]


class LocalLLM:
    """Wrapper for local LLM backends"""
    
    def __init__(self, backend: str = "ollama", model_name: str = "qwen2.5:latest"):
        self.backend = backend
        self.model_name = model_name
        self.llm = None
        
        if backend == "ollama":
            # Ollama runs locally on port 11434
            pass
        elif backend == "llama_cpp":
            # Load model file directly
            model_path = os.getenv("LLAMA_MODEL_PATH")
            if model_path and os.path.exists(model_path):
                self.llm = Llama(model_path=model_path, n_ctx=4096)
    
    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate response using local LLM"""
        try:
            if self.backend == "ollama":
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{'role': 'user', 'content': prompt}],
                    options={'temperature': 0.7, 'num_predict': max_tokens}
                )
                return response['message']['content']
            
            elif self.backend == "llama_cpp" and self.llm:
                response = self.llm(prompt, max_tokens=max_tokens)
                return response['choices'][0]['text']
            
            else:
                return "Local LLM not available. Install ollama or llama-cpp-python"
        
        except Exception as e:
            return f"Error with local LLM: {str(e)}\nEnsure Ollama is running: ollama serve"


class AgenticMonitor:
    """Fully local agentic monitor - no data leaves your machine"""
    
    def __init__(self, 
                 watch_path: str, 
                 model_name: str = "qwen2.5:latest",
                 db_path: str = "./directory_monitor.db"):
        
        self.analyzer = DirectoryAnalyzer(watch_path)
        self.db = LocalDatabase(db_path)
        self.llm = LocalLLM(backend=LLM_BACKEND, model_name=model_name)
        
        if EMBEDDINGS_AVAILABLE:
            self.vector_store = LocalVectorStore(self.db)
        else:
            self.vector_store = None
        
        print(f"✓ All data stored locally in: {os.path.abspath(db_path)}")
        print(f"✓ Using local LLM: {model_name}")
        print(f"✓ Embeddings: {'Local' if EMBEDDINGS_AVAILABLE else 'Disabled'}")
    
    def analyze_with_llm(self, snapshot: DirectorySnapshot) -> Dict[str, Any]:
        """Analyze using local LLM with local RAG context"""
        
        context = ""
        if self.vector_store:
            similar = self.vector_store.search("messy directory violations", top_k=2)
            if similar:
                context = "Previous similar states (stored locally):\n"
                for s in similar:
                    context += f"- {s['snapshot']['timestamp']}: "
                    context += f"{len(s['snapshot']['naming_violations'])} violations\n"
        
        prompt = self._build_analysis_prompt(snapshot, context)
        analysis = self.llm.generate(prompt, max_tokens=800)
        
        return {
            'timestamp': snapshot.timestamp,
            'messiness_score': self._calculate_messiness_score(snapshot),
            'llm_analysis': analysis,
            'snapshot': asdict(snapshot)
        }
    
    def _build_analysis_prompt(self, snapshot: DirectorySnapshot, context: str) -> str:
        """Build prompt for local LLM"""
        max_depth = max(snapshot.depth_distribution.keys()) if snapshot.depth_distribution else 0
        
        prompt = f"""You are a development standards expert. Analyze this directory structure:

{context}

Current State:
- Path: {snapshot.path}
- Total Files: {snapshot.total_files}
- Total Directories: {snapshot.total_dirs}
- Maximum Depth: {max_depth}
- File Types: {', '.join(list(snapshot.file_types.keys())[:10])}
- Naming Violations: {len(snapshot.naming_violations)}

Specific Issues:
{chr(10).join(snapshot.naming_violations[:10])}

Large Files:
{chr(10).join([f"- {f['path']}: {f['size_mb']}MB" for f in snapshot.largest_files[:5]])}

Based on development best practices:
1. Is this directory structure messy? (Yes/No)
2. What are the top 3 issues?
3. What specific actions should be taken?
4. Rate messiness 1-10 (10 = extremely messy)

Be concise and actionable."""
        
        return prompt
    
    def _calculate_messiness_score(self, snapshot: DirectorySnapshot) -> float:
        """Calculate messiness score"""
        score = 0.0
        score += min(len(snapshot.naming_violations) * 0.5, 4.0)
        
        max_depth = max(snapshot.depth_distribution.keys()) if snapshot.depth_distribution else 0
        if max_depth > self.analyzer.standards['max_depth']:
            score += (max_depth - self.analyzer.standards['max_depth']) * 0.5
        
        score += min(len(snapshot.largest_files) * 0.3, 2.0)
        
        if len(snapshot.file_types) > 15:
            score += 1.0
        
        return min(score, 10.0)
    
    def scan_and_alert(self, alert_threshold: float = 5.0) -> Dict[str, Any]:
        """Scan and analyze - everything stays local"""
        snapshot = self.analyzer.scan_directory()
        analysis = self.analyze_with_llm(snapshot)
        
        # Save to local database
        snapshot_id = self.db.save_snapshot(snapshot, analysis['messiness_score'])
        self.db.save_analysis(
            snapshot_id, 
            analysis['llm_analysis'], 
            analysis['messiness_score'] >= alert_threshold
        )
        
        # Update local vector store
        if self.vector_store:
            self.vector_store.add_snapshot(snapshot_id, snapshot)
        
        # Generate alert message
        if analysis['messiness_score'] >= alert_threshold:
            analysis['alert'] = True
            analysis['message'] = f"🚨 ALERT: Messiness score {analysis['messiness_score']:.1f}/10"
        else:
            analysis['alert'] = False
            analysis['message'] = f"✅ Clean (score: {analysis['messiness_score']:.1f}/10)"
        
        return analysis
    
    def get_statistics(self) -> Dict:
        """Get monitoring statistics from local database"""
        return self.db.get_stats()
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get analysis history from local database"""
        return self.db.get_history(limit)
    
    def export_report(self, output_path: str = "./monitor_report.json"):
        """Export report to local file"""
        report = {
            'generated': datetime.now().isoformat(),
            'statistics': self.get_statistics(),
            'recent_history': self.get_history(20)
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✓ Report saved locally: {os.path.abspath(output_path)}")
    
    def cleanup(self):
        """Close database connection"""
        self.db.close()


def main():
    """Example usage - 100% local monitoring"""
    print("🔒 100% Local Agentic RAG Directory Monitor")
    print("=" * 60)
    print("✓ No cloud APIs - all processing on your machine")
    print("✓ All data stored in local SQLite database")
    print("✓ Local LLM via Ollama")
    print("✓ Local embeddings via sentence-transformers")
    print()
    
    # Configuration
    WATCH_PATH = "."
    CHECK_INTERVAL = 300  # 5 minutes
    ALERT_THRESHOLD = 5.0
    MODEL_NAME = "qwen2.5:latest"  # or llama3.2:latest, codellama:latest
    
    # Load custom standards from local config
    DevelopmentStandards.load_from_file()
    
    print(f"Watching: {os.path.abspath(WATCH_PATH)}")
    print(f"Local Model: {MODEL_NAME}")
    print(f"Alert Threshold: {ALERT_THRESHOLD}/10")
    print(f"Check Interval: {CHECK_INTERVAL}s\n")
    
    monitor = AgenticMonitor(WATCH_PATH, MODEL_NAME)
    
    try:
        while True:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scanning...")
            
            result = monitor.scan_and_alert(alert_threshold=ALERT_THRESHOLD)
            
            print(f"\n{result['message']}")
            print(f"\nLocal LLM Analysis:\n{result['llm_analysis']}")
            
            if result['alert']:
                print("\n⚠️  Consider cleaning up your directory!")
                # Could trigger local notification (no external services)
            
            # Show stats
            stats = monitor.get_statistics()
            print(f"\nStats: {stats['total_scans']} scans, "
                  f"avg messiness: {stats['avg_messiness']}/10")
            
            print(f"\nNext scan in {CHECK_INTERVAL}s...")
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped")
        
        # Export final report locally
        monitor.export_report()
        
        stats = monitor.get_statistics()
        print(f"\nTotal scans: {stats['total_scans']}")
        print(f"Average messiness: {stats['avg_messiness']}/10")
        
        monitor.cleanup()
        print("\n✓ All data saved locally in ./directory_monitor.db")


if __name__ == "__main__":
    main()
