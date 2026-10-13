"""Print the GitHub release notes for VERSION from CHANGELOG.md.

Takes the ``## [VERSION]`` section, unwraps its hard-wrapped lines (GitHub
renders single newlines in release bodies as line breaks) and adds a Full
Changelog link to the previous version. Used by build-release.yml.

    python3 scripts/release-notes.py 1.3.2 > notes.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = "https://github.com/I4cTime/protonshift"


def notes(changelog: str, version: str) -> str:
    heads = list(re.finditer(r"^## \[(\d+\.\d+\.\d+)\].*$", changelog, re.MULTILINE))
    idx = next((i for i, m in enumerate(heads) if m.group(1) == version), None)
    if idx is None:
        raise SystemExit(f"CHANGELOG.md has no [{version}] section")
    end = heads[idx + 1].start() if idx + 1 < len(heads) else len(changelog)
    body = changelog[heads[idx].end():end]

    blocks: list[str] = []
    for line in body.splitlines():
        if not line.strip():
            blocks.append("")
        elif line.startswith((" ", "\t")) and blocks and blocks[-1]:
            blocks[-1] += " " + line.strip()  # continuation of the line above
        else:
            blocks.append(line.rstrip())
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(blocks)).strip()
    # a blank line after each heading, as in earlier releases
    text = re.sub(r"^(###[^\n]*)\n(?!\n)", r"\1\n\n", text, flags=re.MULTILINE)

    out = f"## ProtonShift {version}\n\n{text}\n"
    if idx + 1 < len(heads):
        prev = heads[idx + 1].group(1)
        out += f"\n**Full Changelog**: {REPO}/compare/v{prev}...v{version}\n"
    return out


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    print(notes((root / "CHANGELOG.md").read_text(encoding="utf-8"), sys.argv[1]), end="")
