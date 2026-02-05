"""Update DocToc-style TOCs without requiring Node.

This script rewrites only the content between the standard DocToc markers:

    <!-- START doctoc generated TOC please keep comment here to allow auto update -->
    ... (generated content) ...
    <!-- END doctoc generated TOC please keep comment here to allow auto update -->

It scans Markdown headings (H1-H3) outside code blocks, builds anchors, and
replaces the TOC block in-place. Explicit heading IDs like `{#custom-id}` are
respected and used verbatim.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path


START = "<!-- START doctoc generated TOC please keep comment here to allow auto update -->"
END = "<!-- END doctoc generated TOC please keep comment here to allow auto update -->"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
CODE_FENCE_RE = re.compile(r"^```")


def _slugify(text: str) -> str:
    """Convert a heading into a GitHub-style anchor slug."""
    text = text.strip()
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("`", "")
    text = re.sub(r"[^\w\s\-]", "", text, flags=re.UNICODE)
    text = text.strip().lower()
    text = re.sub(r"\s+", "-", text)
    return text


def _extract_toc_lines(lines: list[str]) -> list[str]:
    """Extract TOC entries from headings in the document."""
    toc: list[str] = []
    in_code = False

    for line in lines:
        if CODE_FENCE_RE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue

        match = HEADING_RE.match(line)
        if not match:
            continue

        level = len(match.group(1))
        if level < 1 or level > 3:
            continue

        title = match.group(2).strip()
        if not title:
            continue

        explicit = re.search(r"\{#([^}]+)\}\s*$", title)
        if explicit:
            anchor = explicit.group(1)
            title = re.sub(r"\s*\{#[^}]+\}\s*$", "", title).strip()
        else:
            anchor = _slugify(title)

        indent = "  " * (level - 1)
        toc.append(f"{indent}- [{title}](#{anchor})")

    return toc


def _build_toc_block(toc_lines: list[str]) -> str:
    """Build the final TOC block with standard DocToc markers."""
    block_lines = [
        START,
        "",
        "**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*",
        "",
        *toc_lines,
        "",
        END,
    ]
    return "\n".join(block_lines)


def update_file(path: Path) -> bool:
    """Update a single file in-place. Returns True if modified."""
    text = path.read_text()
    if START not in text or END not in text:
        return False

    pre, rest = text.split(START, 1)
    _old, post = rest.split(END, 1)

    toc_lines = _extract_toc_lines(text.splitlines())
    toc_block = _build_toc_block(toc_lines)

    new_text = pre + "\n" + toc_block + post
    if new_text != text:
        path.write_text(new_text)
        return True
    return False


def update_files(paths: Iterable[Path]) -> list[Path]:
    """Update all files and return those that changed."""
    return [path for path in paths if update_file(path)]


def main() -> None:
    """Update TOCs for the default documentation set."""
    default_files = [
        Path("README.md"),
        Path("docs/index.md"),
        Path("docs/usage.md"),
        Path("docs/dev/refactoring-2026.md"),
        Path("CHANGELOG.md"),
        Path("CONTRIBUTING.md"),
    ]

    updated = update_files(default_files)
    if updated:
        files = "\n".join(f"- {path}" for path in updated)
        print("Updated TOCs in:\n" + files)
    else:
        print("No TOC changes needed.")


if __name__ == "__main__":
    main()
