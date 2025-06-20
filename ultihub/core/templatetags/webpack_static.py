import json
from pathlib import Path

from django import template
from django.conf import settings

from ultihub.settings import ENVIRONMENT

register = template.Library()
_manifest_cache = None


@register.simple_tag
def webpack_static(filename: str) -> str:
    """
    Load the webpack static file with the given filename.
    If the file is not found in the manifest, return the original.
    """
    global _manifest_cache
    if _manifest_cache is None or ENVIRONMENT == "dev":  # type: ignore[unreachable]
        manifest_path = Path(settings.WEBPACK_DIST_DIR) / "manifest.json"
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                _manifest_cache = json.load(f)
        except FileNotFoundError:
            _manifest_cache = {}

    hashed_filename = _manifest_cache.get(filename, filename)
    return hashed_filename
