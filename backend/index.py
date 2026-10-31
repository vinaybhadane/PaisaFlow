"""Vercel entry point for FastAPI backend service (index.py alias)."""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.app.main import app

__all__ = ["app"]

