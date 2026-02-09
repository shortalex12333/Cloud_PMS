import os
import sys
import importlib
from pathlib import Path


def test_type_precedence_env_merges_with_defaults(monkeypatch):
    """
    Ensure TYPE_PRECEDENCE_JSON from env merges with defaults so that
    missing keys like brand/document/approval_status do NOT fall back to 'other'.
    """
    # Provide an env override that intentionally omits several critical keys
    # and overrides one key to verify that override wins over default
    monkeypatch.setenv(
        'TYPE_PRECEDENCE_JSON',
        '{"model": 77, "part_number": 81, "custom_only": 42}'
    )

    # Ensure repo root is on sys.path so 'apps' package can be imported
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Reload the module to apply env var
    mod = importlib.import_module('apps.api.extraction.extraction_config')
    importlib.reload(mod)

    cfg = mod.config

    # Overridden keys should reflect env values
    assert cfg.type_precedence.get('model') == 77
    assert cfg.type_precedence.get('part_number') == 81
    # New custom key allowed via env
    assert cfg.type_precedence.get('custom_only') == 42

    # Defaults that were NOT present in env must still be present (merge)
    assert cfg.type_precedence.get('brand') == 82
    assert cfg.type_precedence.get('document_type') == 78
    assert cfg.type_precedence.get('document') == 75
    assert cfg.type_precedence.get('approval_status') == 68
    assert cfg.type_precedence.get('shopping_list_term') == 66

    # 'other' must remain defined and non-zero
    assert cfg.type_precedence.get('other') == 10
