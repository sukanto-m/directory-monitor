#!/usr/bin/env python3
"""Test script to verify all installations"""

def test_imports():
    """Test all Python imports"""
    print("Testing Python imports...")
    
    try:
        import ollama
        print("✓ ollama")
    except ImportError:
        print("✗ ollama")
    
    try:
        from sentence_transformers import SentenceTransformer
        print("✓ sentence-transformers")
    except ImportError:
        print("✗ sentence-transformers")
    
    try:
        import numpy
        print("✓ numpy")
    except ImportError:
        print("✗ numpy")
    
    try:
        import flask
        print("✓ flask")
    except ImportError:
        print("✗ flask")
    
    try:
        from rich.console import Console
        print("✓ rich")
    except ImportError:
        print("✗ rich")
    
    try:
        import matplotlib
        print("✓ matplotlib")
    except ImportError:
        print("✗ matplotlib")

def test_ollama():
    """Test Ollama connection"""
    print("\nTesting Ollama connection...")
    
    try:
        import ollama
        models = ollama.list()
        print(f"✓ Ollama connected")
        print(f"  Available models: {len(models.get('models', []))}")
        
        model_names = [m['name'] for m in models.get('models', [])]
        if any('qwen' in m for m in model_names):
            print("  ✓ Qwen model found")
        else:
            print("  ⚠ Qwen model not found - Run: ollama pull qwen2.5:latest")
            
    except Exception as e:
        print(f"✗ Ollama error: {e}")
        print("  Make sure Ollama is running: ollama serve")

def test_embeddings():
    """Test sentence transformers"""
    print("\nTesting embeddings model...")
    
    try:
        from sentence_transformers import SentenceTransformer
        print("  Downloading embedding model (first time only)...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✓ Embeddings model ready")
    except Exception as e:
        print(f"✗ Embeddings error: {e}")

if __name__ == "__main__":
    print("🔧 Directory Monitor - Setup Verification\n")
    print("=" * 50)
    
    test_imports()
    test_ollama()
    test_embeddings()
    
    print("\n" + "=" * 50)
    print("✅ Setup verification complete!\n")
