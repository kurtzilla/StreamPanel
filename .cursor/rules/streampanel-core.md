---
description: StreamPanel-wide conventions for Cursor Agent (scope, docs layout, Python)
alwaysApply: true
---

# StreamPanel core

- **`.cursor/`** — Use only for **Cursor** rules and optional Cursor-specific notes. **Not** for product roadmaps or general documentation; use @docs/ and @docs/plans/README.md for that.
- **Layout**: Use @README.md as the repo map; package identity @pyproject.toml — do not duplicate name/version in chat.
- **Scope**: Touch only what the task needs; avoid drive-by refactors.
- **Consistency**: Match existing Python layout and patterns in this repo.
- **Python**: Prefer focused rules with `globs: **/*.py` when adding language-specific guidance (formatters/linters live in `pyproject.toml`).

Cursor supports `.md` or `.mdc` for rules; rename this file if you prefer `.mdc`.
