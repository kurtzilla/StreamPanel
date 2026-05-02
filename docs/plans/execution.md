# Execution queue (StreamPanel v1)

Todo ids match the **Stream Panel CTk App** Cursor plan. **One active row** at a time; update status when you merge.

| Todo id | Status | Branch / PR | Notes |
|---------|--------|-------------|-------|
| `scaffold-package` | done | — | `python -m streampanel`, `pyproject` + `src/streampanel` |
| `sqlite-store` | done | — | `store.py`, `shortcuts_folder.py`, `tests/test_store.py` |
| `window-chrome` | done | — | `window_chrome.py`: borderless strip, drag, Settings/Add link stubs, Close |
| `panel-behavior` | done | — | Pin + Win `WS_EX_TOOLWINDOW` ([`win_overlay.py`](src/streampanel/win_overlay.py)), `app_kv` + [`store.py`](src/streampanel/store.py) geometry/`sn`, [`panel_layout.py`](src/streampanel/panel_layout.py) min–max H (cols=4 stub), ghost add row, debounced persist in [`app.py`](src/streampanel/app.py). |
| `deck-grid-ui` | next | | |
| `deck-item-editor` | pending | | |
| `add-link-ux` | pending | | |
| `settings-persist` | pending | | |
| `settings-window-ui` | pending | | |
| `launch-tracker` | pending | | |
| `manual-verify` | pending | | |
| `onboarding-docs` | pending | | |
| `runtime-shell` | pending | | |
| `backup-scale-ui` | pending | | |
| `deck-ops-diagnostics` | pending | | |
| `v1-stretch-features` | pending | | |
| `portable-a11y` | pending | | |
| `git-upstream` | pending | | |

**Status:** `pending` → `next` → `in progress` → `done`.
