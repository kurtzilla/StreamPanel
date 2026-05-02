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
| `settings-persist` | done | | |
| `settings-window-ui` | done | | |
| `launch-tracker` | done | | |
| `manual-verify` | done | — | **In-scope slice:** done rows through `add-link-ux` (excludes `settings-persist` / `settings-window-ui` / `launch-tracker` until merged). **2026-05-01:** `python -m unittest discover -s tests -p "test_*.py" -v` — 26 OK; `streampanel.store` / `deck_grid` / dialogs import OK. **Windows UI:** hand-verify chrome strip, pin + overlay, geometry persist, folder sync + status line, deck grid (+ ghosts), Settings, Add link, Item editor. |
| `onboarding-docs` | next | | End-user [`docs/getting-started.md`](../getting-started.md) + contributor [`docs/developing.md`](../developing.md); README "Onboarding" pointers + [`docs/README.md`](../README.md) index updated. |
| `runtime-shell` | done | | |
| `backup-scale-ui` | done | | |
| `deck-ops-diagnostics` | done | — | Deck drag-reorder ([`deck_grid.py`](src/streampanel/deck_grid.py), [`app.py`](src/streampanel/app.py)); [`merge_full_order_after_visible_reorder`](src/streampanel/store.py) + tests; Settings About/Diagnostics + copy ([`settings_dialog.py`](src/streampanel/settings_dialog.py)); [`getting-started.md`](../getting-started.md) troubleshooting. |
| `v1-stretch-features` | done | — | Shared launch [`item_launch.py`](src/streampanel/item_launch.py); [`list_launch_events_for_item`](src/streampanel/store.py) + tests; Channels lower pane notes + activity ([`channels_view.py`](src/streampanel/channels_view.py)); Settings **Primary deck click** + `deck_primary_action`; deck filter + delayed primary / double-click launch + reorder off when filtered ([`app.py`](src/streampanel/app.py), [`deck_grid.py`](src/streampanel/deck_grid.py)); optional tile `CTkImage` from `icon_path`. **Manual:** filter + reorder cleared; Channels history after view/launch; both primary modes; double-click launch when Open Channels. **2026-05-01:** `python -m unittest discover -s tests -p "test_*.py" -v` — 34 OK. |
| `theme-system` | done | | |
| `portable-a11y` | pending | | |
| `git-upstream` | pending | | |

**Status:** `pending` → `next` → `in progress` → `done`.
