# Execution queue (StreamPanel v1)

Todo ids match the **Stream Panel CTk App** Cursor plan. **One active row** at a time; update status when you merge.

| Todo id | Status | Branch / PR | Notes |
|---------|--------|-------------|-------|
| `scaffold-package` | done | — | `python -m streampanel`, `pyproject` + `src/streampanel` |
| `sqlite-store` | done | — | `store.py`, `shortcuts_folder.py`, `tests/test_store.py` |
| `window-chrome` | done | — | `window_chrome.py`: borderless strip, drag, Settings/Add link stubs, Close |
| `panel-behavior` | done | — | Pin + Win `WS_EX_TOOLWINDOW` ([`win_overlay.py`](src/streampanel/win_overlay.py)), `app_kv` + [`store.py`](src/streampanel/store.py) geometry/`sn`, [`panel_layout.py`](src/streampanel/panel_layout.py) min–max H (cols=4 stub), ghost add row, debounced persist in [`app.py`](src/streampanel/app.py). |
| `deck-grid-ui` | done | — | [`deck_grid.py`](src/streampanel/deck_grid.py): `DEFAULT_GRID_COLS` grid, sort_order cells, `+` / `+ add` ghosts, extra row near max height; [`app.py`](src/streampanel/app.py) wires stub item/add. |
| `deck-item-editor` | done | — | [`item_editor.py`](src/streampanel/item_editor.py): modal label/notes/`confirm_launch`; `update_item` `clear_label_override` / `clear_notes`; app refresh + sync. |
| `add-link-ux` | done | — | [`add_link_dialog.py`](src/streampanel/add_link_dialog.py): `.url` from URL + optional stem; [`app.py`](src/streampanel/app.py) `reload_deck`; tests [`test_add_link.py`](tests/test_add_link.py). |
| `settings-persist` | next | | |
| `settings-window-ui` | pending | | |
| `launch-tracker` | pending | | |
| `manual-verify` | done | — | **In-scope slice:** done rows through `add-link-ux` (excludes `settings-persist` / `settings-window-ui` / `launch-tracker` until merged). **2026-05-01:** `python -m unittest discover -s tests -p "test_*.py" -v` — 26 OK; `streampanel.store` / `deck_grid` / dialogs import OK. **Windows UI:** hand-verify chrome strip, pin + overlay, geometry persist, folder sync + status line, deck grid (+ ghosts), Settings, Add link, Item editor. |
| `onboarding-docs` | next | | End-user [`docs/getting-started.md`](../getting-started.md) + contributor [`docs/developing.md`](../developing.md); README "Onboarding" pointers + [`docs/README.md`](../README.md) index updated. |
| `runtime-shell` | pending | | |
| `backup-scale-ui` | pending | | |
| `deck-ops-diagnostics` | pending | | |
| `v1-stretch-features` | pending | | |
| `portable-a11y` | pending | | |
| `git-upstream` | pending | | |

**Status:** `pending` → `next` → `in progress` → `done`.
