"""Generate frontend language packs (Jed 1.x JSON) from .po files.

Usage: python scripts/translations/po_to_json.py [translations_dir]
"""

import json
import sys
from pathlib import Path

from babel.messages.pofile import read_po

base = Path(sys.argv[1] if len(sys.argv) > 1 else "superset/translations")

for po_path in base.glob("*/LC_MESSAGES/messages.po"):
    lang = po_path.parent.parent.name
    with po_path.open("rb") as f:
        catalog = read_po(f)
    data = {"": {"domain": "superset", "plural_forms": catalog.plural_forms, "lang": lang}}
    for msg in catalog:
        if not msg.id or msg.fuzzy:
            continue
        if isinstance(msg.id, (list, tuple)):
            key, values = msg.id[0], [s or "" for s in msg.string]
        else:
            key, values = msg.id, [msg.string or ""]
        if any(values):
            data[key] = values
    out = {"domain": "superset", "locale_data": {"superset": data}}
    json_path = po_path.with_suffix(".json")
    json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{json_path}: {len(data) - 1} entries")
