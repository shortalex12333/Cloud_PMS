"""Action Router Dispatchers"""

from . import internal_dispatcher
from . import n8n_dispatcher

__all__ = [
    "internal_dispatcher",
    "n8n_dispatcher",
]
