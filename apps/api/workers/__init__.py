"""
CelesteOS Background Workers

Workers run as separate processes on Render.

Each worker is designed to be imported directly (e.g., python -m workers.embedding_worker_1536).
Lazy imports prevent cross-dependencies from causing import errors.
"""


def __getattr__(name):
    """Lazy import to prevent dependency issues between workers."""
    if name == 'EmailWatcherWorker':
        from .email_watcher_worker import EmailWatcherWorker
        return EmailWatcherWorker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ['EmailWatcherWorker']
