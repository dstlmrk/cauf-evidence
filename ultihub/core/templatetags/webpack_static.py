import json
from pathlib import Path

from django import template
from django.conf import settings

register = template.Library()
_manifest_cache = None


@register.simple_tag
def webpack_static(filename: str) -> str:
    """
    Load the webpack static file with the given filename.
    If the file is not found in the manifest, return the original.
    """
    global _manifest_cache
    if _manifest_cache is None:
        manifest_path = Path(settings.BASE_DIR) / "static" / "dist" / "manifest.json"
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                _manifest_cache = json.load(f)
        except FileNotFoundError:
            _manifest_cache = {}

    return _manifest_cache.get(filename, filename)
