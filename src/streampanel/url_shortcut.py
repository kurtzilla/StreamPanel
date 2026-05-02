"""Parse and write Windows Internet Shortcut (.url) INI files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, urlunparse


@dataclass(frozen=True)
class ParsedInternetShortcut:
    """Fields read from ``[InternetShortcut]`` in a ``.url`` file."""

    url: str
    icon_file: str | None
    icon_index: int
    working_directory: str | None


def normalize_url(raw: str) -> str:
    s = raw.strip()
    if not s:
        raise ValueError("URL is empty.")
    parsed = urlparse(s)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://.")
    netloc = parsed.netloc
    if not netloc:
        raise ValueError("URL must include a host (e.g. https://example.com).")
    netloc = netloc.lower()
    return urlunparse(
        (parsed.scheme.lower(), netloc, parsed.path or "", "", parsed.query, parsed.fragment)
    )


def internet_shortcut_body(
    url: str,
    *,
    icon_file: str | None = None,
    icon_index: int = 0,
) -> str:
    lines = ["[InternetShortcut]", f"URL={url}"]
    if icon_file:
        lines.append(f"IconFile={icon_file}")
        lines.append(f"IconIndex={int(icon_index)}")
    return "\n".join(lines) + "\n"


def _parse_ini_section(lines: list[str], section_name: str) -> dict[str, str]:
    """Line-oriented INI: case-insensitive section and keys; first key wins."""
    section_lower = section_name.lower()
    in_section = False
    out: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_section = line[1:-1].strip().lower() == section_lower
            continue
        if not in_section:
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip().lower()
        val = v.strip()
        if key not in out:
            out[key] = val
    return out


def parse_internet_shortcut(path: Path) -> ParsedInternetShortcut:
    """Read a ``.url`` file and return parsed fields. Raises ``ValueError`` if unusable."""
    p = path.expanduser()
    if not p.is_file():
        raise ValueError("Not a file.")
    if p.suffix.lower() != ".url":
        raise ValueError("Expected a .url file.")
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise ValueError(str(e)) from e
    kv = _parse_ini_section(text.splitlines(), "InternetShortcut")
    raw_url = kv.get("url", "").strip()
    if not raw_url:
        raise ValueError("Missing URL= in [InternetShortcut].")
    url = normalize_url(raw_url)
    icon_file = kv.get("iconfile", "").strip() or None
    wd = kv.get("workingdirectory", "").strip() or None
    icon_index = 0
    if "iconindex" in kv:
        try:
            icon_index = int(kv["iconindex"].strip())
        except ValueError:
            icon_index = 0
    return ParsedInternetShortcut(
        url=url,
        icon_file=icon_file,
        icon_index=icon_index,
        working_directory=wd,
    )


_SINGLE_URL_RE = re.compile(
    r"^https?://[^\s]+$",
    re.IGNORECASE,
)


def looks_like_single_http_url(text: str) -> bool:
    s = text.strip()
    return bool(s) and bool(_SINGLE_URL_RE.match(s))
