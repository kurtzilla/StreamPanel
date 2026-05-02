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

## Git: fork and `upstream`

If you work from a **fork**, keep **two remotes**:

- **`origin`** — your fork (the default after `git clone` of the fork).
- **`upstream`** — the canonical StreamPanel repo, so you can pull changes from maintainers before you open or update a PR.

The canonical project URL lives in [`pyproject.toml`](../pyproject.toml) under **`[project.urls]`** (**Repository**). For Git, use that page’s clone URL or:

`https://github.com/kurtzilla/StreamPanel.git`

The default branch is **`master`**. If the project renames it, substitute the new name in the commands below.

**One-time:** add `upstream` and confirm remotes (same commands in PowerShell, Command Prompt, or Git Bash):

```bash
git remote add upstream https://github.com/kurtzilla/StreamPanel.git
git remote -v
```

If `upstream` already exists with the wrong URL, run `git remote set-url upstream https://github.com/kurtzilla/StreamPanel.git` instead.

**Sync** your topic branch before pushing:

```bash
git fetch upstream
```

Then either **merge** upstream into your branch:

```bash
git switch your-branch
git merge upstream/master
```

or **rebase** your commits on top of upstream:

```bash
git switch your-branch
git rebase upstream/master
```

Either approach is fine; pick what keeps your PR easy to review and matches any guidance from maintainers.

**Open a PR:** push to your fork and open the pull request against the canonical repo:

```bash
git push -u origin your-branch
```

If you cloned the canonical repository directly, `origin` may already be the canonical remote; you only need `upstream` when `origin` is your fork.

## Package tour

`src/streampanel/` is a flat module layout (src layout per [`pyproject.toml`](../pyproject.toml)):

- [`__main__.py`](../src/streampanel/__main__.py) — `python -m streampanel` entry; calls `app.run`.
- [`app.py`](../src/streampanel/app.py) — wires the CTk root, toolbar callbacks, deck reload, and debounced geometry persist.
- [`store.py`](../src/streampanel/store.py) — SQLite schema/migrations, `DeckItem`, `AppSettings`, `PanelShellState`, sync from the shortcuts folder, CRUD, launch events, `app_kv` key/value.
- [`shortcuts_folder.py`](../src/streampanel/shortcuts_folder.py) — User-data + shortcuts folder resolution (`%APPDATA%\StreamPanel\` defaults; optional `STREAMPANEL_DATA_DIR` for a portable data root).
- [`panel_layout.py`](../src/streampanel/panel_layout.py) — pure layout math: `MIN_PANEL_WIDTH`, `min_panel_height`, `max_panel_height`, `clamp_root_geometry`.
- [`window_chrome.py`](../src/streampanel/window_chrome.py) — borderless top strip, move icon + title drag surface, ghost drag preview, optional display picker + gear Settings + Close.
- [`win_overlay.py`](../src/streampanel/win_overlay.py) — Windows-only: `WS_EX_TOOLWINDOW` when the main window is unfocused (no taskbar slot); cleared on `FocusIn` so a taskbar button appears while the panel is active.
- [`single_instance.py`](../src/streampanel/single_instance.py) — One main process per `user_data_dir`: Windows named mutex + HWND JSON for second-instance foreground; POSIX `flock` lock file.
- [`deck_grid.py`](../src/streampanel/deck_grid.py) — `DeckGridView`: cell rendering and `+` ghost add slots in the last partial row.
- [`themes.py`](../src/streampanel/themes.py) — palette presets (`THEME_IDS`), dialog backgrounds, `apply_theme` / `clamp_theme_id`.
- [`panel_dnd.py`](../src/streampanel/panel_dnd.py) — optional drag-and-drop onto the main window (`install_panel_drop_handlers`; requires `tkinterdnd2`).
- [`icon_image.py`](../src/streampanel/icon_image.py) — optional deck tile `CTkImage` from `icon_path` (PIL).
- [`add_link_dialog.py`](../src/streampanel/add_link_dialog.py) — modal that writes a `.url` into the shortcuts folder.
- [`item_editor.py`](../src/streampanel/item_editor.py) — modal for label override, notes, `confirm_launch`, hide-from-deck.
- [`settings_dialog.py`](../src/streampanel/settings_dialog.py) — modal for appearance, shortcuts folder override, deck columns, show-hidden toggle.
- [`channels_view.py`](../src/streampanel/channels_view.py) — primary-click Channels window (notes + recent `launch_events`, **Launch** → [`item_launch.py`](../src/streampanel/item_launch.py) / [`runtime_shell.py`](../src/streampanel/runtime_shell.py)).
- [`item_launch.py`](../src/streampanel/item_launch.py) — confirm-if-flag, `open_path`, record `launch` event (shared by Channels and direct deck launch).

## Tests

Tests live under [`tests/`](../tests/) and are discovered by the `test_*.py` glob:

- [`test_store.py`](../tests/test_store.py) — schema, sync, CRUD, settings, panel shell state.
- [`test_panel_layout.py`](../tests/test_panel_layout.py) — height math and geometry clamping.
- [`test_deck_grid.py`](../tests/test_deck_grid.py) — grid rendering helpers.
- [`test_add_link.py`](../tests/test_add_link.py) — URL normalization, filename sanitization, write flow.
- [`test_url_shortcut.py`](../tests/test_url_shortcut.py) — `.url` parse/write helpers, `normalize_url`.
- [`test_shortcuts_folder.py`](../tests/test_shortcuts_folder.py) — `STREAMPANEL_DATA_DIR` and `user_data_dir`.
- [`test_runtime_shell.py`](../tests/test_runtime_shell.py) — `open_path` / `ShellOpenError` (Windows `startfile` mocked where applicable).
- [`test_panel_dnd.py`](../tests/test_panel_dnd.py) — DnD file list parsing (`paths_from_dnd_files`).
- [`test_single_instance.py`](../tests/test_single_instance.py) — Mutex name / path hashing for single-instance guard.
- [`test_window_chrome.py`](../tests/test_window_chrome.py) — `compute_drag_rect` and panel-drag min/max pin semantics.

When adding behaviour, prefer adding focused unit tests next to the existing module's test file rather than introducing new test infrastructure.

## Conventions

These mirror [`.cursor/rules/streampanel-core.md`](../.cursor/rules/streampanel-core.md), which is the source of truth for agent-facing rules:

- Src layout — package code lives under `src/streampanel/`; do not add a top-level `streampanel/` package.
- Focused changes — touch only what the task needs; avoid drive-by refactors. Match the existing patterns rather than introducing new ones inline.
- Persistence goes through `store.py` — schema changes use the `migrate(conn)` ladder (`PRAGMA user_version`); ad-hoc app key/value pairs use `app_kv_get` / `app_kv_set` with a versioned key.
- New modal dialogs follow the pattern in [`settings_dialog.py`](../src/streampanel/settings_dialog.py), [`item_editor.py`](../src/streampanel/item_editor.py), and [`add_link_dialog.py`](../src/streampanel/add_link_dialog.py): `CTkToplevel`, `transient(parent)`, `grab_set()`, `themes.dialog_background()` for `fg_color`, brief `-topmost` flash for focus, and a `dismiss()` helper that releases the grab.
- Errors that must reach the user use `_stub_dialog` from [`window_chrome.py`](../src/streampanel/window_chrome.py).
- Where a module is intentionally Windows-only (`win_overlay.py`), guard with `sys.platform == "win32"` and degrade silently on other platforms.
- [`pyproject.toml`](../pyproject.toml) holds package metadata, dependencies, and setuptools package discovery. This repo does not yet commit a Ruff/Mypy/Black configuration; use local editor or CLI tools if you want them. Do not duplicate package identity (name, version, deps) in prose elsewhere.
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
