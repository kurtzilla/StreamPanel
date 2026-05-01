# Vendor / external code (in-repo)

## Python convention

For dependencies **published on PyPI (or a private index)**, the standard is **not** to copy them into the repo: declare them in **[`pyproject.toml`](../pyproject.toml)** (`[project.dependencies]`) and install into a **virtualenv** (`.venv/`).

Use **`vendor/`** only when you **must** keep code in-tree, for example:

- Git **submodules** of forks or unreleased libs  
- **Vendored** snapshots you patch locally  
- Tarballs you cannot pull from an index  

Avoid duplicating normal dependencies that belong only in `pyproject.toml`.
