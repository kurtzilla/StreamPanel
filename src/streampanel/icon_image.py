"""Load a ``CTkImage`` from a local icon/image path (Pillow)."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk


def load_ctk_image_for_path(path: Path | str, *, size_px: int) -> ctk.CTkImage | None:
    """Return a square ``CTkImage`` or None if missing, unreadable, or Pillow unavailable."""
    p = Path(path)
    if not p.is_file():
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        pil = Image.open(p)
        pil = pil.convert("RGBA")
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS  # type: ignore[attr-defined]
        pil = pil.resize((size_px, size_px), resample)
        return ctk.CTkImage(
            light_image=pil,
            dark_image=pil,
            size=(size_px, size_px),
        )
    except OSError:
        return None
