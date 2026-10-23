"""Discover song-list document links from the approved source pages.

Source A builds its lists in the browser from a JavaScript array literal. That literal is
parsed as data by a small scanner; fetched code is never executed. Sources B and C are
HTML tables. URLs are recorded exactly as published, never built from volume numbers.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .normalize import clean

SECTION_CLASS = "accordion4"
DATA_START = re.compile(r"const\s+songList\s*=\s*")


@dataclass(frozen=True)
class DiscoveredLink:
    source: str
    section: str
    label: str
    url: str


@dataclass(frozen=True)
class LinkDiff:
    added: tuple[DiscoveredLink, ...]
    removed: tuple[DiscoveredLink, ...]
    changed: tuple[
        tuple[DiscoveredLink, DiscoveredLink], ...
    ]  # (before, after) same label, new URL


def _literal_end(text: str, start: int) -> int:
    """Index just past the array literal that begins at `start` (string-aware)."""
    depth, i, quote = 0, start, ""
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = ""
        elif c in "\"'`":
            quote = c
        elif c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unterminated array literal")


def js_literal_to_json(text: str) -> str:
    """Convert a JS object/array literal with bare keys into JSON. Only double-quoted strings."""
    out: list[str] = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i : j + 1])
            i = j + 1
        elif c in "'`":
            raise ValueError("single-quoted and template strings are not supported")
        elif c.isalpha() or c == "_":
            j = i
            while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                j += 1
            k = j
            while k < len(text) and text[k].isspace():
                k += 1
            word = text[i:j]
            out.append(f'"{word}"' if k < len(text) and text[k] == ":" else word)
            i = j
        elif c == ",":
            k = i + 1
            while k < len(text) and text[k].isspace():
                k += 1
            if k < len(text) and text[k] in "]}":
                i += 1  # trailing comma
            else:
                out.append(c)
                i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def parse_source_a(script: str) -> list[DiscoveredLink]:
    match = DATA_START.search(script)
    if not match:
        raise ValueError("songList array not found in the page script")
    start = match.end()
    data = json.loads(js_literal_to_json(script[start : _literal_end(script, start)]))
    try:
        return _links_from_a(data)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"Source A data has an unexpected shape: {exc!r}") from exc


def _text(value: Any) -> str:
    if not isinstance(value, str | int):
        raise TypeError(f"expected text, got {type(value).__name__}")
    return str(value)


def _links_from_a(data: Any) -> list[DiscoveredLink]:
    links: list[DiscoveredLink] = []
    for section in data:
        name = _text(section["product"])
        for v in section.get("volumes", []):
            links.append(
                DiscoveredLink("a", name, f"Volume {_text(v['volume'])}", _text(v["link"]))
            )
        for y in section.get("years", []):
            for m in y.get("months", []):
                label = f"{_text(y['year'])} {_text(m['month'])}"
                links.append(DiscoveredLink("a", name, label, _text(m["link"])))
    return links


class _TableParser(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.links: list[DiscoveredLink] = []
        self._section = ""
        self._in_section_button = False
        self._in_td = False
        self._label: str | None = None
        self._cell: list[str] = []
        self._hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "button" and SECTION_CLASS in (a.get("class") or "").split():
            self._in_section_button, self._section = True, ""
        elif tag == "tr":
            self._label, self._hrefs = None, []
        elif tag == "td":
            self._in_td, self._cell = True, []
        elif tag == "a" and (a.get("href") or "").startswith("http"):
            self._hrefs.append(a.get("href") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "button":
            self._in_section_button = False
        elif tag == "td" and self._in_td:
            self._in_td = False
            text = clean("".join(self._cell))
            if self._label is None and text:
                self._label = text
        elif tag == "tr" and self._section and self._label:
            for href in self._hrefs:
                self.links.append(DiscoveredLink(self.source, self._section, self._label, href))
            self._label, self._hrefs = None, []

    def handle_data(self, data: str) -> None:
        if self._in_section_button:
            self._section += data
        elif self._in_td:
            self._cell.append(data)


def parse_html_sections(html: str, source: str) -> list[DiscoveredLink]:
    parser = _TableParser(source)
    parser.feed(html)
    return [
        DiscoveredLink(link.source, clean(link.section), link.label, link.url)
        for link in parser.links
    ]


def diff_links(previous: list[DiscoveredLink], current: list[DiscoveredLink]) -> LinkDiff:
    """Compare two discoveries. A link that disappears is reported, never silently dropped."""
    before = {(link.source, link.section, link.label): link for link in previous}
    after = {(link.source, link.section, link.label): link for link in current}
    added = tuple(after[k] for k in after if k not in before)
    removed = tuple(before[k] for k in before if k not in after)
    changed = tuple(
        (before[k], after[k]) for k in after if k in before and before[k].url != after[k].url
    )
    return LinkDiff(added, removed, changed)


def save_links(path: str | Path, links: list[DiscoveredLink]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps([asdict(link) for link in links], indent=1), encoding="utf-8")


def load_links(path: str | Path) -> list[DiscoveredLink]:
    raw: list[dict[str, Any]] = json.loads(Path(path).read_text(encoding="utf-8"))
    return [DiscoveredLink(**item) for item in raw]
