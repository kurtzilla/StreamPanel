# StreamPanel

Single index for humans and agents: layout, Cursor workflow, status.

**Package metadata** (name, version, authors): [`pyproject.toml`](pyproject.toml) — do not duplicate in prose.

## Repository layout

| Path | Purpose |
|------|---------|
| [`pyproject.toml`](pyproject.toml) | Python project metadata & packaging (`[project]`, version **0.0.0**) |
| [`.cursor/`](.cursor/) | **Cursor IDE only** — Agent rules under [`.cursor/rules/`](.cursor/rules/). Not general docs → see [`docs/cursor.md`](docs/cursor.md) |
| [`.project/`](.project/) | Workspace for notes, ideas, misc files—tracked but not app source ([readme](.project/README.md)) |
| [`.scripts/`](.scripts/) | Build helpers, scripts—tracked; does not ship with the app ([readme](.scripts/README.md)) |
| [`src/`](src/) | Application source (Python package layout TBD) |
| [`vendor/`](vendor/README.md) | Optional **in-repo** vendored/submodule trees—**not** where normal PyPI deps live ([`pyproject.toml`](pyproject.toml)) |
| [`docs/`](docs/) | **Shared documentation** — plans, ADRs, guides ([`docs/README.md`](docs/README.md)) |
| [`.env/`](.env/) | Environment templates and local-only env files ([`.env/.env.example`](.env/.env.example) committed) |
| [`AGENTS.md`](AGENTS.md) | Optional agent entry: links to rules + this README |

## Environment variables

- **Committed:** [`.env/.env.example`](.env/.env.example) — template only.
- **Local:** Copy to another name under `.env/`, add secrets, keep out of git. See [`.gitignore`](.gitignore).

## Cursor (IDE) workflow

- **Rules:** [`.cursor/rules/`](.cursor/rules/) (start with [`streampanel-core.md`](.cursor/rules/streampanel-core.md)).
- **Product plans & docs:** [`docs/plans/`](docs/plans/README.md) and [`docs/`](docs/README.md)—not under `.cursor/`. See [`docs/cursor.md`](docs/cursor.md).

## Status

Scaffold: Python `pyproject.toml` present; app entry and run instructions to follow.
