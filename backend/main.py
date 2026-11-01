"""Vercel entry point for FastAPI backend service."""

import os
import sys
import types

# Ensure both backend root and parent directory are in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)

for path in [backend_dir, parent_dir]:
    if path and path not in sys.path:
        sys.path.insert(0, path)

# Synthesize 'backend' in sys.modules if not already available so all internal imports resolve
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
