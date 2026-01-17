"""
CelesteOS Background Workers

Workers run as separate processes on Render.
"""

from .email_watcher_worker import EmailWatcherWorker

__all__ = ['EmailWatcherWorker']
