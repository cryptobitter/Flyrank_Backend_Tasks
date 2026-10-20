"""
Application Entry Point for AI Image Matching Engine.

Usage:
    python main.py
    uvicorn app.main:app --port 8000 --reload
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting FlyRank AI Image Matching Engine on http://localhost:{port}...")
    uvicorn.run(app, host=host, port=port)
