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
| [`src/streampanel/`](src/streampanel/) | Python package (`python -m streampanel`) |
| [`vendor/`](vendor/README.md) | Optional **in-repo** vendored/submodule trees—**not** where normal PyPI deps live ([`pyproject.toml`](pyproject.toml)) |
| [`docs/`](docs/) | **Shared documentation** — plans, ADRs, guides ([`docs/README.md`](docs/README.md)) |
| [`.env/`](.env/) | Environment templates and local-only env files ([`.env/.env.example`](.env/.env.example) committed) |
| [`AGENTS.md`](AGENTS.md) | Optional agent entry: links to rules + this README |

## Environment variables

- **Committed:** [`.env/.env.example`](.env/.env.example) — template only.
- **Local:** Copy to another name under `.env/`, add secrets, keep out of git. See [`.gitignore`](.gitignore).

## Cursor (IDE) workflow

- **Rules:** [`.cursor/rules/`](.cursor/rules/) (start with [`streampanel-core.md`](.cursor/rules/streampanel-core.md)).
- **Product plans & docs:** [`docs/plans/`](docs/plans/README.md) (includes **[execution queue](docs/plans/execution.md)**) and [`docs/`](docs/README.md)—not under `.cursor/`. See [`docs/cursor.md`](docs/cursor.md).

## Run (dev)

From repo root:

```bash
pip install -e .
python -m streampanel
```

(`streampanel` console script is installed too; ensure your Python **Scripts** directory is on `PATH` if the command is not found.)

Tests:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## Onboarding

- **Quick start** (end users): [`docs/getting-started.md`](docs/getting-started.md) — first-run layout, toolbar, add link, item editor, settings, window behaviour, troubleshooting.
- **Develop** (contributors): [`docs/developing.md`](docs/developing.md) — package tour, tests, conventions, plans / execution-queue workflow, Cursor/agent pointers.

## Status

**Execution queue:** [`docs/plans/execution.md`](docs/plans/execution.md). **Next:** **`onboarding-docs`**. **`git-upstream`** done — fork and `upstream` remote in [`docs/developing.md`](docs/developing.md); canonical repo under [`pyproject.toml`](pyproject.toml) `[project.urls]`.
