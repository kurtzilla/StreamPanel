"""SQLite persistence for deck items: migrations, sync from shortcuts folder, CRUD, reorder."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from streampanel.shortcuts_folder import default_db_path, default_shortcuts_dir

ALLOWED_SUFFIXES = {".lnk", ".url"}


@dataclass(frozen=True)
class DeckItem:
    id: int
    source_path: str
    sort_order: int
    grid_row: int | None
    grid_col: int | None
    label_override: str | None
    icon_path: str | None
    notes: str | None
    flags_json: str | None
    viewer_rect_x: int | None
    viewer_rect_y: int | None
    viewer_rect_w: int | None
    viewer_rect_h: int | None

    @staticmethod
    def from_row(row: sqlite3.Row) -> DeckItem:
        return DeckItem(
            id=int(row["id"]),
            source_path=str(row["source_path"]),
            sort_order=int(row["sort_order"]),
            grid_row=row["grid_row"],
            grid_col=row["grid_col"],
            label_override=row["label_override"],
            icon_path=row["icon_path"],
            notes=row["notes"],
            flags_json=row["flags_json"],
            viewer_rect_x=row["viewer_rect_x"],
            viewer_rect_y=row["viewer_rect_y"],
            viewer_rect_w=row["viewer_rect_w"],
            viewer_rect_h=row["viewer_rect_h"],
        )


@dataclass(frozen=True)
class SyncResult:
    added_paths: tuple[str, ...]
    removed_ids: tuple[int, ...]


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    version = int(cur.execute("PRAGMA user_version").fetchone()[0])
    if version < 1:
        cur.executescript(
            """
            CREATE TABLE deck_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL UNIQUE COLLATE NOCASE,
                sort_order INTEGER NOT NULL,
                grid_row INTEGER,
                grid_col INTEGER,
                label_override TEXT,
                icon_path TEXT,
                notes TEXT,
                flags_json TEXT,
                viewer_rect_x INTEGER,
                viewer_rect_y INTEGER,
                viewer_rect_w INTEGER,
                viewer_rect_h INTEGER
            );
            CREATE INDEX idx_deck_items_sort ON deck_items(sort_order);
            PRAGMA user_version = 1;
            """
        )
        conn.commit()


def list_shortcut_files(folder: Path) -> frozenset[str]:
    folder = folder.resolve()
    if not folder.is_dir():
        return frozenset()
    out: set[str] = set()
    for p in folder.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        out.add(str(p.resolve()))
    return frozenset(out)


def _next_sort_order(cur: sqlite3.Cursor) -> int:
    row = cur.execute(
        "SELECT COALESCE(MAX(sort_order), -1) FROM deck_items"
    ).fetchone()
    return int(row[0]) + 1


def sync_from_folder(
    conn: sqlite3.Connection,
    folder: Path | None = None,
) -> SyncResult:
    """Insert rows for new *.lnk/*.url files; delete rows for missing files."""
    folder = (folder or default_shortcuts_dir()).resolve()
    on_disk = list_shortcut_files(folder)
    cur = conn.cursor()

    rows = cur.execute("SELECT id, source_path FROM deck_items").fetchall()
    by_path: dict[str, int] = {
        str(Path(r["source_path"]).resolve()): int(r["id"]) for r in rows
    }

    added: list[str] = []
    removed_ids: list[int] = []

    for path in sorted(on_disk):
        if path not in by_path:
            so = _next_sort_order(cur)
            cur.execute(
                """
                INSERT INTO deck_items (
                    source_path, sort_order,
                    grid_row, grid_col,
                    label_override, icon_path, notes, flags_json,
                    viewer_rect_x, viewer_rect_y, viewer_rect_w, viewer_rect_h
                ) VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, NULL,
                          NULL, NULL, NULL, NULL)
                """,
                (path, so),
            )
            added.append(path)
            new_id = int(cur.execute("SELECT last_insert_rowid()").fetchone()[0])
            by_path[path] = new_id

    for path, row_id in list(by_path.items()):
        if path not in on_disk:
            cur.execute("DELETE FROM deck_items WHERE id = ?", (row_id,))
            removed_ids.append(row_id)

    conn.commit()
    return SyncResult(added_paths=tuple(added), removed_ids=tuple(removed_ids))


def list_items(conn: sqlite3.Connection) -> list[DeckItem]:
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT * FROM deck_items ORDER BY sort_order ASC, id ASC"
    ).fetchall()
    return [DeckItem.from_row(r) for r in rows]


def get_item(conn: sqlite3.Connection, item_id: int) -> DeckItem | None:
    cur = conn.cursor()
    row = cur.execute(
        "SELECT * FROM deck_items WHERE id = ?", (item_id,)
    ).fetchone()
    return DeckItem.from_row(row) if row else None


def delete_item(conn: sqlite3.Connection, item_id: int) -> bool:
    cur = conn.cursor()
    cur.execute("DELETE FROM deck_items WHERE id = ?", (item_id,))
    conn.commit()
    return cur.rowcount > 0


def update_item(
    conn: sqlite3.Connection,
    item_id: int,
    *,
    sort_order: int | None = None,
    grid_row: int | None = None,
    grid_col: int | None = None,
    label_override: str | None = None,
    icon_path: str | None = None,
    notes: str | None = None,
    flags: dict[str, Any] | None = None,
    viewer_rect: tuple[int, int, int, int] | None = None,
    clear_viewer_rect: bool = False,
) -> bool:
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM deck_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return False

    item = DeckItem.from_row(row)
    flags_json = item.flags_json
    if flags is not None:
        flags_json = json.dumps(flags)

    vx, vy, vw, vh = (
        item.viewer_rect_x,
        item.viewer_rect_y,
        item.viewer_rect_w,
        item.viewer_rect_h,
    )
    if clear_viewer_rect:
        vx = vy = vw = vh = None
    elif viewer_rect is not None:
        vx, vy, vw, vh = viewer_rect

    new_sort = sort_order if sort_order is not None else item.sort_order
    new_gr = grid_row if grid_row is not None else item.grid_row
    new_gc = grid_col if grid_col is not None else item.grid_col
    new_label = (
        label_override if label_override is not None else item.label_override
    )
    new_icon = icon_path if icon_path is not None else item.icon_path
    new_notes = notes if notes is not None else item.notes

    cur.execute(
        """
        UPDATE deck_items SET
            sort_order = ?, grid_row = ?, grid_col = ?,
            label_override = ?, icon_path = ?, notes = ?, flags_json = ?,
            viewer_rect_x = ?, viewer_rect_y = ?, viewer_rect_w = ?, viewer_rect_h = ?
        WHERE id = ?
        """,
        (
            new_sort,
            new_gr,
            new_gc,
            new_label,
            new_icon,
            new_notes,
            flags_json,
            vx,
            vy,
            vw,
            vh,
            item_id,
        ),
    )
    conn.commit()
    return True


def reorder_items(conn: sqlite3.Connection, ordered_ids: Iterable[int]) -> None:
    cur = conn.cursor()
    for i, item_id in enumerate(ordered_ids):
        cur.execute(
            "UPDATE deck_items SET sort_order = ? WHERE id = ?", (i, item_id)
        )
    conn.commit()


def parse_flags(item: DeckItem) -> dict[str, Any]:
    if not item.flags_json:
        return {}
    try:
        data = json.loads(item.flags_json)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}
