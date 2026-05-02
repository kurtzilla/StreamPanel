# Getting started

StreamPanel is a small CustomTkinter "Stream Deck"-style launcher panel — a borderless, pinnable window that surfaces your saved shortcuts in a grid you can launch with a click. This guide walks through installing it, the first-run layout on disk, and the day-to-day toolbar / deck / settings flows.

For the repo map and where each file lives, see the root [`README.md`](../README.md). For contributor setup, see [`developing.md`](developing.md).

## Install and run

Requires Python 3.11+. From a clone of the repo:

```bash
pip install -e .
python -m streampanel
```

The `streampanel` console script is installed alongside the editable package. If `streampanel` is not found, add your Python `Scripts/` directory to `PATH` (same note as in the root [`README.md`](../README.md)).

## First-run layout on disk

On first launch, StreamPanel creates a per-user data folder and a SQLite database, then scans an adjacent shortcuts folder. Defaults come from [`src/streampanel/shortcuts_folder.py`](../src/streampanel/shortcuts_folder.py):

- User data dir: `%APPDATA%\StreamPanel\` on Windows, falling back to `~/StreamPanel/` if `APPDATA` is not set.
- Database: `streampanel.db` inside the user data dir (`default_db_path`).
- Shortcuts folder: `shortcuts/` inside the user data dir (`default_shortcuts_dir`). You can point this at any other directory in Settings.

On every start the panel auto-syncs from the shortcuts folder: any `.lnk` or `.url` file there becomes a deck item, and items whose source file disappears are dropped (`ALLOWED_SUFFIXES` and `sync_from_folder` in [`src/streampanel/store.py`](../src/streampanel/store.py)). The status text near the top of the panel shows the current count and the sync delta.

## The toolbar

The top strip ([`src/streampanel/window_chrome.py`](../src/streampanel/window_chrome.py)) replaces the native title bar. Left-to-right:

- Drag region — click-and-drag anywhere on "StreamPanel — drag here to move" to reposition the window.
- Pin on / Pin off — toggles always-on-top. The state is persisted across sessions.
- Settings — opens the modal in [`src/streampanel/settings_dialog.py`](../src/streampanel/settings_dialog.py).
- Add link — opens the modal in [`src/streampanel/add_link_dialog.py`](../src/streampanel/add_link_dialog.py).
- Close — saves geometry and exits.

## Adding a link

Click "Add link" on the toolbar (or any `+` ghost cell on the deck). Provide:

- URL — must start with `http://` or `https://` and include a host. The URL is normalized (lower-cased scheme/host) and saved.
- Filename (optional) — without the `.url` extension. If left blank, the host (and a short slug from the path) is used. Invalid Windows filename characters are replaced and collisions get a numeric suffix.

The dialog writes a Windows internet shortcut (`[InternetShortcut]\nURL=…`) into the shortcuts folder, then triggers a deck reload (`reload_deck` in [`src/streampanel/app.py`](../src/streampanel/app.py)) so the new item appears immediately.

To add a Windows application or local file, drop a `.lnk` into the shortcuts folder yourself (e.g. via Explorer "Send to" or "Create shortcut"); StreamPanel will pick it up on the next sync.

## Editing a deck item

- Left-click a deck cell — opens the item in the Channels viewer ([`src/streampanel/channels_view.py`](../src/streampanel/channels_view.py); a stub today, the lower pane lands later) and records a launch event.
- Right-click a deck cell — opens the item editor ([`src/streampanel/item_editor.py`](../src/streampanel/item_editor.py)) with:
  - Display label (empty falls back to the source filename stem).
  - Notes (free-form text).
  - "Confirm before system launch" — sets the `confirm_launch` flag for the future system-launch path.
  - "Hide from deck" — keeps the item in the library but removes it from the grid (toggle visibility from Settings).

Source path is shown read-only; changing where a shortcut lives means moving the file on disk and letting sync reconcile.

## Settings

The Settings modal ([`src/streampanel/settings_dialog.py`](../src/streampanel/settings_dialog.py)) covers:

- Appearance — `dark`, `light`, or `system` (`APPEARANCE_MODES` in [`src/streampanel/store.py`](../src/streampanel/store.py)).
- Shortcuts folder — leave empty for the default; otherwise pick an existing directory. Invalid or missing paths fall back to the default.
- Deck columns — `GRID_COLS_MIN`..`GRID_COLS_MAX` (currently 2–8). Column count drives both grid layout and the panel's min/max height.
- Show items hidden from deck on the grid — surfaces items flagged with hide-from-deck so you can edit them again.

Changes apply immediately on Save: appearance is re-applied, the deck rebuilds, and the panel resizes to fit the new column count.

## Window behaviour

The shell is borderless and resizable within bounds derived from the current item count and column count ([`src/streampanel/panel_layout.py`](../src/streampanel/panel_layout.py)). Position, size, screen number, and pin state are debounced-persisted via `save_panel_shell_state` in [`src/streampanel/store.py`](../src/streampanel/store.py), so closing and reopening the panel restores the same spot.

On Windows the panel sets `WS_EX_TOOLWINDOW` ([`src/streampanel/win_overlay.py`](../src/streampanel/win_overlay.py)) so it does not occupy a taskbar slot. Click-through is intentionally not enabled.

## Troubleshooting

- `streampanel` command not found — ensure your Python `Scripts/` directory is on `PATH`, or invoke `python -m streampanel`.
- CustomTkinter install errors — verify `pip install -e .` finished cleanly; the runtime depends on `customtkinter>=5.2` and `pillow>=10` (declared in [`pyproject.toml`](../pyproject.toml)).
- Wrong shortcuts folder — open Settings, confirm the path, and clear the field to fall back to the default `%APPDATA%\StreamPanel\shortcuts\`.
- Deck item gone after sync — confirm the underlying `.lnk` / `.url` file still exists in the shortcuts folder; sync removes items whose source path is missing.
- Window opens off-screen — geometry is clamped on next launch (`clamp_root_geometry` in [`src/streampanel/panel_layout.py`](../src/streampanel/panel_layout.py)); if you ever need a hard reset, delete `streampanel.db` from the user data dir (this also clears items, settings, and launch history).
