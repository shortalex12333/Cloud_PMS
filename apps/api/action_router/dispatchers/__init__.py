"""Action Router Dispatchers"""

from . import internal_dispatcher  # legacy — kept for router.py backwards compat
from . import index                 # new domain-split dispatcher

__all__ = [
    "internal_dispatcher",
    "index",
]
