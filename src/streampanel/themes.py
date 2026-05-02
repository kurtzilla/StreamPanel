"""Low-chroma panel tints: shell, strip, deck, dialogs. Kept subtle so the UI stays behind the player."""

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


@dataclass(frozen=True)
class ThemeSpec:
    dark: ThemePalette
    light: ThemePalette


def _spec(
    dark: ThemePalette,
    light: ThemePalette,
) -> ThemeSpec:
    return ThemeSpec(dark=dark, light=light)


# Dark palettes: small hue bias, similar luminance to baseline charcoal.
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
_FOREST_L = ThemePalette(
    shell_bg="#f2f4f3",
    strip_bg="#e9ecea",
    strip_button_hover="#d8deda",
    deck_cell="#dfe5e1",
    deck_cell_hover="#d2d9d4",
    ghost_cell="#e8edea",
    ghost_cell_hover="#dce3de",
    close_fg="#9f6060",
    close_hover="#af7070",
    dialog_bg="#f2f4f3",
    drag_hint_text=("gray35", "gray40"),
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
_LAVENDER_L = ThemePalette(
    shell_bg="#f3f2f5",
    strip_bg="#eae8ee",
    strip_button_hover="#dad7e0",
    deck_cell="#e0dde4",
    deck_cell_hover="#d3d0d8",
    ghost_cell="#e9e6ed",
    ghost_cell_hover="#dcd9e2",
    close_fg="#9a6090",
    close_hover="#aa70a0",
    dialog_bg="#f3f2f5",
    drag_hint_text=("gray35", "gray40"),
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
_SLATE_L = ThemePalette(
    shell_bg="#f2f3f6",
    strip_bg="#e9ebf0",
    strip_button_hover="#d8dce3",
    deck_cell="#dfe3ea",
    deck_cell_hover="#d2d7e0",
    ghost_cell="#e8ebf1",
    ghost_cell_hover="#dbdfe6",
    close_fg="#9d6060",
    close_hover="#ad7070",
    dialog_bg="#f2f3f6",
    drag_hint_text=("gray35", "gray40"),
)

_THEME_SPECS: dict[str, ThemeSpec] = {
    "charcoal": _spec(_CHARCOAL_D, _CHARCOAL_L),
    "ocean": _spec(_OCEAN_D, _OCEAN_L),
    "forest": _spec(_FOREST_D, _FOREST_L),
    "ember": _spec(_EMBER_D, _EMBER_L),
    "lavender": _spec(_LAVENDER_D, _LAVENDER_L),
    "slate": _spec(_SLATE_D, _SLATE_L),
}

THEME_IDS: tuple[str, ...] = tuple(_THEME_SPECS.keys())
_THEME_IDS_SET = frozenset(THEME_IDS)

THEME_LABELS: dict[str, str] = {
    "charcoal": "Charcoal",
    "ocean": "Cool gray (slight blue)",
    "forest": "Cool gray (slight green)",
    "ember": "Warm gray",
    "lavender": "Soft gray (slight violet)",
    "slate": "Blue-gray",
}


_active: ThemePalette = _CHARCOAL_D
_active_id: str = "charcoal"


def default_theme_id() -> str:
    return THEME_IDS[0]


def clamp_theme_id(raw: str | None) -> str:
    if isinstance(raw, str) and raw in _THEME_IDS_SET:
        return raw
    return default_theme_id()


def _effective_appearance(appearance_mode: str) -> str:
    if appearance_mode == "light":
        return "light"
    if appearance_mode == "dark":
        return "dark"
    g = str(ctk.get_appearance_mode()).lower()
    return "light" if g == "light" else "dark"


def resolve_palette(theme_id: str, appearance_mode: str) -> ThemePalette:
    tid = clamp_theme_id(theme_id)
    spec = _THEME_SPECS[tid]
    return spec.light if _effective_appearance(appearance_mode) == "light" else spec.dark


def apply_theme(theme_id: str, appearance_mode: str) -> None:
    """Set global CTk widget theme (once) and cache the resolved palette for widgets."""
    global _active, _active_id
    ctk.set_default_color_theme(_CTK_WIDGET_THEME)
    _active_id = clamp_theme_id(theme_id)
    _active = resolve_palette(_active_id, appearance_mode)


def current_palette() -> ThemePalette:
    return _active


def current_theme_id() -> str:
    return _active_id


def dialog_background() -> str:
    return _active.dialog_bg
