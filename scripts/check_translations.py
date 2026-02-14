#!/usr/bin/env python3
"""Check that all translation strings in .po files have translations."""

import sys
from pathlib import Path

LOCALE_DIR = Path(__file__).resolve().parent.parent / "ultihub" / "locale"


def check_po_file(po_path: Path) -> list[str]:
    """Check a .po file for missing translations. Returns list of untranslated msgids."""
    missing = []
    current_msgid = ""
    current_msgstr = ""
    in_msgid = False
    in_msgstr = False

    lines = po_path.read_text(encoding="utf-8").splitlines()

    for line in lines:
        line = line.strip()

        if line.startswith("msgid "):
            # Save previous entry
            if in_msgstr and current_msgid and not current_msgstr:
                missing.append(current_msgid)

            current_msgid = line[7:-1]  # Strip 'msgid "' and '"'
            current_msgstr = ""
            in_msgid = True
            in_msgstr = False

        elif line.startswith("msgstr "):
            current_msgstr = line[8:-1]  # Strip 'msgstr "' and '"'
            in_msgid = False
            in_msgstr = True

        elif line.startswith('"') and line.endswith('"'):
            content = line[1:-1]
            if in_msgid:
                current_msgid += content
            elif in_msgstr:
                current_msgstr += content

        elif line == "" or line.startswith("#"):
            if in_msgstr and current_msgid and not current_msgstr:
                missing.append(current_msgid)
            if line == "":
                in_msgid = False
                in_msgstr = False

    # Check last entry
    if in_msgstr and current_msgid and not current_msgstr:
        missing.append(current_msgid)

    return missing


def main() -> int:
    errors = 0

    for lang_dir in LOCALE_DIR.iterdir():
        if not lang_dir.is_dir() or lang_dir.name == "en":
            continue

        po_file = lang_dir / "LC_MESSAGES" / "django.po"
        if not po_file.exists():
            print(f"ERROR: Missing .po file: {po_file}")
            errors += 1
            continue

        missing = check_po_file(po_file)
        if missing:
            print(f"ERROR: {len(missing)} untranslated string(s) in {po_file}:")
            for msgid in missing[:10]:
                print(f'  - "{msgid}"')
            if len(missing) > 10:
                print(f"  ... and {len(missing) - 10} more")
            errors += 1

    if errors:
        print(f"\nTranslation check failed with {errors} error(s).")
        return 1

    print("All translations are complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
