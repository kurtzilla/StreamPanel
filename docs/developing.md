# Developing

Contributor onboarding for StreamPanel: how to get the dev loop running, where the moving parts live, and how the plans / execution queue drives the work.

For the canonical repo map (top-level dirs and what they hold), see the root [`README.md`](../README.md). For the end-user walkthrough, see [`getting-started.md`](getting-started.md).

## Dev loop

Requires Python 3.11+. From the repo root:

```bash
pip install -e .
python -m streampanel
```

Run the test suite (uses `unittest`, no extra deps):

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

This is the same recipe used by the `manual-verify` row in [`docs/plans/execution.md`](plans/execution.md); please run it before opening a PR.

## Package tour

`src/streampanel/` is a flat module layout (src layout per [`pyproject.toml`](../pyproject.toml)):

- [`__main__.py`](../src/streampanel/__main__.py) — `python -m streampanel` entry; calls `app.run`.
- [`app.py`](../src/streampanel/app.py) — wires the CTk root, toolbar callbacks, deck reload, and debounced geometry persist.
- [`store.py`](../src/streampanel/store.py) — SQLite schema/migrations, `DeckItem`, `AppSettings`, `PanelShellState`, sync from the shortcuts folder, CRUD, launch events, `app_kv` key/value.
- [`shortcuts_folder.py`](../src/streampanel/shortcuts_folder.py) — Windows-first user-data + shortcuts folder resolution (`%APPDATA%\StreamPanel\` defaults).
- [`panel_layout.py`](../src/streampanel/panel_layout.py) — pure layout math: `MIN_PANEL_WIDTH`, `min_panel_height`, `max_panel_height`, `clamp_root_geometry`.
- [`window_chrome.py`](../src/streampanel/window_chrome.py) — borderless top strip, drag region, Pin / Settings / Add link / Close buttons.
- [`win_overlay.py`](../src/streampanel/win_overlay.py) — Windows-only `WS_EX_TOOLWINDOW` overlay (no taskbar slot).
- [`deck_grid.py`](../src/streampanel/deck_grid.py) — `DeckGridView`: cell rendering, `+` / `+ add` ghosts, optional extra row near max height.
- [`add_link_dialog.py`](../src/streampanel/add_link_dialog.py) — modal that writes a `.url` into the shortcuts folder.
- [`item_editor.py`](../src/streampanel/item_editor.py) — modal for label override, notes, `confirm_launch`, hide-from-deck.
- [`settings_dialog.py`](../src/streampanel/settings_dialog.py) — modal for appearance, shortcuts folder override, deck columns, show-hidden toggle.
- [`channels_view.py`](../src/streampanel/channels_view.py) — primary-click Channels window (**Launch** → [`runtime_shell.py`](../src/streampanel/runtime_shell.py)); lower pane later.

## Tests

Tests live under [`tests/`](../tests/) and are discovered by the `test_*.py` glob:

- [`test_store.py`](../tests/test_store.py) — schema, sync, CRUD, settings, panel shell state.
- [`test_panel_layout.py`](../tests/test_panel_layout.py) — height math and geometry clamping.
- [`test_deck_grid.py`](../tests/test_deck_grid.py) — grid rendering helpers.
- [`test_add_link.py`](../tests/test_add_link.py) — URL normalization, filename sanitization, write flow.

When adding behaviour, prefer adding focused unit tests next to the existing module's test file rather than introducing new test infrastructure.

## Conventions

These mirror [`.cursor/rules/streampanel-core.md`](../.cursor/rules/streampanel-core.md), which is the source of truth for agent-facing rules:

- Src layout — package code lives under `src/streampanel/`; do not add a top-level `streampanel/` package.
- Focused changes — touch only what the task needs; avoid drive-by refactors. Match the existing patterns rather than introducing new ones inline.
- Persistence goes through `store.py` — schema changes use the `migrate(conn)` ladder (`PRAGMA user_version`); ad-hoc app key/value pairs use `app_kv_get` / `app_kv_set` with a versioned key.
- New modal dialogs follow the pattern in [`settings_dialog.py`](../src/streampanel/settings_dialog.py), [`item_editor.py`](../src/streampanel/item_editor.py), and [`add_link_dialog.py`](../src/streampanel/add_link_dialog.py): `CTkToplevel`, `transient(parent)`, `grab_set()`, `COLOR_BG`, brief `-topmost` flash for focus, and a `dismiss()` helper that releases the grab.
- Errors that must reach the user use `_stub_dialog` from [`window_chrome.py`](../src/streampanel/window_chrome.py).
- Where a module is intentionally Windows-only (`win_overlay.py`), guard with `sys.platform == "win32"` and degrade silently on other platforms.
- Lint/format config lives in [`pyproject.toml`](../pyproject.toml). Do not duplicate package identity (name, version, deps) in prose elsewhere.
- General docs belong under [`docs/`](README.md) — `.cursor/` is reserved for Cursor IDE rules and Cursor-specific notes only ([`docs/cursor.md`](cursor.md)).

## Plans and the execution queue

Multi-part work is tracked in [`docs/plans/execution.md`](plans/execution.md). Each row is a Cursor plan todo id with columns: Status, Branch / PR, Notes.

Workflow:

- One active row at a time. Status flow is `pending` → `next` → `in progress` → `done`.
- When you start a row, set it to `in progress` (or `next` if you are about to pick it up) and fill the Branch / PR column.
- When the PR merges, mark the row `done` and add a brief Notes summary that points to the touched files.
- Add new rows only when the corresponding Cursor plan adds a todo id; keep the file ordered to match the plan.

Narrative plans and longer write-ups belong alongside the queue under [`docs/plans/`](plans/README.md). Link the current narrative plan from the root [`README.md`](../README.md) Status section when one is active.

## Cursor and agents

- [`AGENTS.md`](../AGENTS.md) at the repo root is a short pointer into the rules + README.
- [`.cursor/rules/streampanel-core.md`](../.cursor/rules/streampanel-core.md) is the always-applied core rule for the Cursor agent.
- [`docs/cursor.md`](cursor.md) explains what belongs in `.cursor/` versus this `docs/` tree.
