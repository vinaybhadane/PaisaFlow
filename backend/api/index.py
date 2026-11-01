"""Vercel entry point for FastAPI backend service in api/index.py."""

import os
import sys
import types

api_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(api_dir)
parent_dir = os.path.dirname(backend_dir)

for path in [backend_dir, parent_dir]:
    if path and path not in sys.path:
        sys.path.insert(0, path)

if "backend" not in sys.modules:
    try:
        import backend  # noqa: F401
    except ModuleNotFoundError:
        backend_pkg = types.ModuleType("backend")
        backend_pkg.__path__ = [backend_dir]
        backend_pkg.__file__ = os.path.join(backend_dir, "__init__.py")
        sys.modules["backend"] = backend_pkg

from backend.app.main import app

__all__ = ["app"]

