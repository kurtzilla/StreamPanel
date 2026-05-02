"""Panel themes: shell, strip, deck, dialogs. Each theme fixes its own light/dark appearance."""

from __future__ import annotations

from dataclasses import dataclass

import customtkinter as ctk

# One restrained CTk accent for all tints (avoid rainbow chrome).
_CTK_WIDGET_THEME = "dark-blue"


@dataclass(frozen=True)
class ThemePalette:
    shell_bg: str
    strip_bg: str
    strip_button_hover: str
    deck_cell: str
    deck_cell_hover: str
    ghost_cell: str
    ghost_cell_hover: str
    close_fg: str
    close_hover: str
    dialog_bg: str
    drag_hint_text: tuple[str, str]


# --- Dark bases (existing hues) ---
_CHARCOAL_D = ThemePalette(
    shell_bg="#1e1e1e",
    strip_bg="#252526",
    strip_button_hover="#3d3d3d",
    deck_cell="#323232",
    deck_cell_hover="#404040",
    ghost_cell="#2a2a2a",
    ghost_cell_hover="#3d3d3d",
    close_fg="#8b3a3a",
    close_hover="#a44444",
    dialog_bg="#1e1e1e",
    drag_hint_text=("gray70", "gray65"),
)
_OCEAN_D = ThemePalette(
    shell_bg="#1c1e22",
    strip_bg="#23262c",
    strip_button_hover="#343840",
    deck_cell="#2e3238",
    deck_cell_hover="#3c4048",
    ghost_cell="#25282e",
    ghost_cell_hover="#363a42",
    close_fg="#844848",
    close_hover="#955252",
    dialog_bg="#1c1e22",
    drag_hint_text=("gray70", "gray65"),
)
_FOREST_D = ThemePalette(
    shell_bg="#1c201e",
    strip_bg="#252925",
    strip_button_hover="#343a36",
    deck_cell="#2e3430",
    deck_cell_hover="#3c423e",
    ghost_cell="#252b28",
    ghost_cell_hover="#363c38",
    close_fg="#834848",
    close_hover="#945252",
    dialog_bg="#1c201e",
    drag_hint_text=("gray70", "gray65"),
)
_EMBER_D = ThemePalette(
    shell_bg="#201e1c",
    strip_bg="#2a2624",
    strip_button_hover="#3a3632",
    deck_cell="#38342f",
    deck_cell_hover="#45403a",
    ghost_cell="#2b2825",
    ghost_cell_hover="#393632",
    close_fg="#8b4038",
    close_hover="#9c4a42",
    dialog_bg="#201e1c",
    drag_hint_text=("gray70", "gray65"),
)
_LAVENDER_D = ThemePalette(
    shell_bg="#1e1c22",
    strip_bg="#26242b",
    strip_button_hover="#38353e",
    deck_cell="#343038",
    deck_cell_hover="#403c45",
    ghost_cell="#29262c",
    ghost_cell_hover="#373440",
    close_fg="#844868",
    close_hover="#955278",
    dialog_bg="#1e1c22",
    drag_hint_text=("gray70", "gray65"),
)
_SLATE_D = ThemePalette(
    shell_bg="#1c1f24",
    strip_bg="#24282e",
    strip_button_hover="#353a42",
    deck_cell="#30353c",
    deck_cell_hover="#3d424b",
    ghost_cell="#262a30",
    ghost_cell_hover="#363b44",
    close_fg="#804848",
    close_hover="#915252",
    dialog_bg="#1c1f24",
    drag_hint_text=("gray70", "gray65"),
)
_MOCHA_D = ThemePalette(
    shell_bg="#261f1b",
    strip_bg="#322a25",
    strip_button_hover="#443a32",
    deck_cell="#3d342e",
    deck_cell_hover="#4c4139",
    ghost_cell="#2d2520",
    ghost_cell_hover="#3a322c",
    close_fg="#8b4a38",
    close_hover="#9c5844",
    dialog_bg="#261f1b",
    drag_hint_text=("gray70", "gray65"),
)
_MONOKAI_D = ThemePalette(
    shell_bg="#272822",
    strip_bg="#3e3d32",
    strip_button_hover="#49483e",
    deck_cell="#3e3d32",
    deck_cell_hover="#49483e",
    ghost_cell="#2f302b",
    ghost_cell_hover="#3d3c38",
    close_fg="#f92672",
    close_hover="#fd5e9a",
    dialog_bg="#272822",
    drag_hint_text=("#75715e", "#75715e"),
)

# --- Light (reuse prior light variants) ---
_CHARCOAL_L = ThemePalette(
    shell_bg="#f4f4f4",
    strip_bg="#ececec",
    strip_button_hover="#dadada",
    deck_cell="#e2e2e2",
    deck_cell_hover="#d6d6d6",
    ghost_cell="#ebebeb",
    ghost_cell_hover="#dedede",
    close_fg="#a85a5a",
    close_hover="#b86a6a",
    dialog_bg="#f4f4f4",
    drag_hint_text=("gray35", "gray40"),
)
_OCEAN_L = ThemePalette(
    shell_bg="#f2f3f5",
    strip_bg="#e9ebef",
    strip_button_hover="#d8dce2",
    deck_cell="#dfe2e8",
    deck_cell_hover="#d2d6de",
    ghost_cell="#e8eaee",
    ghost_cell_hover="#dce0e6",
    close_fg="#a06060",
    close_hover="#b07070",
    dialog_bg="#f2f3f5",
    drag_hint_text=("gray35", "gray40"),
)
_EMBER_L = ThemePalette(
    shell_bg="#f5f3f2",
    strip_bg="#edeae8",
    strip_button_hover="#ddd9d6",
    deck_cell="#e3dfdc",
    deck_cell_hover="#d7d2ce",
    ghost_cell="#ece9e6",
    ghost_cell_hover="#e0dcd8",
    close_fg="#a06558",
    close_hover="#b07568",
    dialog_bg="#f5f3f2",
    drag_hint_text=("gray35", "gray40"),
)

_THEME_PALETTES: dict[str, ThemePalette] = {
    "charcoal": _CHARCOAL_D,
    "ocean": _OCEAN_D,
    "forest": _FOREST_D,
    "ember": _EMBER_D,
    "lavender": _LAVENDER_D,
    "slate": _SLATE_D,
    "mocha": _MOCHA_D,
    "monokai": _MONOKAI_D,
    "snow": _CHARCOAL_L,
    "mist": _OCEAN_L,
    "sand": _EMBER_L,
}

THEME_APPEARANCE: dict[str, str] = {
    "charcoal": "dark",
    "ocean": "dark",
    "forest": "dark",
    "ember": "dark",
    "lavender": "dark",
    "slate": "dark",
    "mocha": "dark",
    "monokai": "dark",
    "snow": "light",
    "mist": "light",
    "sand": "light",
}

THEME_IDS: tuple[str, ...] = tuple(_THEME_PALETTES.keys())
_THEME_IDS_SET = frozenset(THEME_IDS)

THEME_LABELS: dict[str, str] = {
    "charcoal": "Charcoal",
    "ocean": "Ocean",
    "forest": "Forest",
    "ember": "Ember",
    "lavender": "Lavender",
    "slate": "Slate",
    "mocha": "Mocha",
    "monokai": "Monokai",
    "snow": "Snow",
    "mist": "Mist",
    "sand": "Sand",
}

_active: ThemePalette = _CHARCOAL_D
_active_id: str = "charcoal"


def default_theme_id() -> str:
    return THEME_IDS[0]


def clamp_theme_id(raw: str | None) -> str:
    if isinstance(raw, str) and raw in _THEME_IDS_SET:
        return raw
    return default_theme_id()


def theme_appearance(theme_id: str) -> str:
    tid = clamp_theme_id(theme_id)
    return THEME_APPEARANCE.get(tid, "dark")


def palette_for(theme_id: str) -> ThemePalette:
    return _THEME_PALETTES[clamp_theme_id(theme_id)]


def resolve_palette(theme_id: str, appearance_mode: str | None = None) -> ThemePalette:
    """Resolve palette for ``theme_id``. ``appearance_mode`` is ignored (each theme is fixed)."""
    return palette_for(theme_id)


def apply_theme(theme_id: str, appearance_mode: str | None = None) -> None:
    """Set global CTk widget theme (once) and cache the palette for ``theme_id``."""
    global _active, _active_id
    ctk.set_default_color_theme(_CTK_WIDGET_THEME)
    _active_id = clamp_theme_id(theme_id)
    _active = palette_for(_active_id)


def current_palette() -> ThemePalette:
    return _active


def current_theme_id() -> str:
    return _active_id


def dialog_background() -> str:
    return _active.dialog_bg
