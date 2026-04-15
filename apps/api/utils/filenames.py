"""Filename sanitisation utilities.

Single source of truth for filenames that are going INTO Supabase Storage
as object paths. Not for HTTP Content-Disposition headers (use
routes/email.py:sanitize_filename for that — different rules apply).

Extracted 2026-04-15 from duplicated copies in:
- handlers/document_handlers.py:269 (_sanitize_filename)
- routes/document_routes.py:97       (_sanitize_filename, was duplicated
                                     during the POST /v1/documents/upload work)
Both now import from this module.
"""

import re


def sanitize_storage_filename(filename: str) -> str:
    """Sanitize a user-supplied filename for use as a Supabase Storage object path.

    Guarantees:
    - No path separators (/, \\, :, NUL → _)
    - No leading dots (hidden files)
    - No leading/trailing whitespace
    - ≤ 255 chars, preserving extension where possible
    - Never empty — falls back to 'document'

    This is a defence-in-depth check. Callers must ALSO scope the full storage
    path under the caller's yacht_id as the first segment (enforced by
    internal_dispatcher.py:342 startswith check).
    """
    if not filename:
        return 'document'

    safe = re.sub(r'[/\\:\x00]', '_', filename.strip())
    safe = safe.lstrip('.')

    if len(safe) > 255:
        if '.' in safe:
            name, ext = safe.rsplit('.', 1)
            safe = name[:255 - len(ext) - 1] + '.' + ext
        else:
            safe = safe[:255]

    return safe or 'document'
