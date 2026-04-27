# routes/handlers/fault_handler.py — re-export shim
# Canonical fault logic lives in handlers/fault_handler.py.
# This file exists only to satisfy the relative import in routes/handlers/__init__.py.
from handlers.fault_handler import HANDLERS  # noqa: F401
