"""SQLite persistence for deck items: migrations, sync from shortcuts folder, CRUD, reorder."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from streampanel.panel_layout import DEFAULT_GRID_COLS
from streampanel.shortcuts_folder import default_db_path, default_shortcuts_dir

ALLOWED_SUFFIXES = {".lnk", ".url"}
FLAG_HIDE_FROM_DECK = "hide_from_deck"


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
    version = int(cur.execute("PRAGMA user_version").fetchone()[0])
    if version < 2:
        cur.executescript(
            """
            CREATE TABLE app_kv (
                key TEXT PRIMARY KEY NOT NULL,
                value TEXT NOT NULL
            );
            PRAGMA user_version = 2;
            """
        )
        conn.commit()
    version = int(cur.execute("PRAGMA user_version").fetchone()[0])
    if version < 3:
        cur.executescript(
            """
            CREATE TABLE launch_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                source_path TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'view'
            );
            CREATE INDEX idx_launch_events_item ON launch_events(item_id, opened_at);
            PRAGMA user_version = 3;
            """
        )
        conn.commit()


_K_ALWAYS_TOP = "panel_always_on_top_v1"
_K_GEOM = "panel_window_geometry_v1"
_K_APP_SETTINGS = "app_settings_v1"

APPEARANCE_MODES: tuple[str, ...] = ("dark", "light", "system")
_APPEARANCE_MODES = frozenset(APPEARANCE_MODES)
GRID_COLS_MIN = 2
GRID_COLS_MAX = 8

UI_SCALE_MIN = 0.85
UI_SCALE_MAX = 1.75
UI_SCALE_DEFAULT = 1.0


def app_kv_get(conn: sqlite3.Connection, key: str) -> str | None:
    cur = conn.cursor()
    row = cur.execute("SELECT value FROM app_kv WHERE key = ?", (key,)).fetchone()
    return str(row[0]) if row else None


def app_kv_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO app_kv (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    conn.commit()


@dataclass(frozen=True)
class PanelShellState:
    always_on_top: bool
    x: int | None
    y: int | None
    w: int | None
    h: int | None
    screen_number: int | None


def load_panel_shell_state(conn: sqlite3.Connection) -> PanelShellState:
    top_s = app_kv_get(conn, _K_ALWAYS_TOP)
    always_on_top = top_s == "1" if top_s is not None else False
    raw = app_kv_get(conn, _K_GEOM)
    if not raw:
        return PanelShellState(always_on_top, None, None, None, None, None)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return PanelShellState(always_on_top, None, None, None, None, None)
    if not isinstance(data, dict):
        return PanelShellState(always_on_top, None, None, None, None, None)
    try:
        x = int(data["x"])
        y = int(data["y"])
        w = int(data["w"])
        h = int(data["h"])
        sn = data.get("sn")
        screen_number = int(sn) if sn is not None else None
    except (KeyError, TypeError, ValueError):
        return PanelShellState(always_on_top, None, None, None, None, None)
    return PanelShellState(always_on_top, x, y, w, h, screen_number)


def save_panel_shell_state(
    conn: sqlite3.Connection,
    *,
    always_on_top: bool,
    x: int,
    y: int,
    w: int,
    h: int,
    screen_number: int,
) -> None:
    app_kv_set(conn, _K_ALWAYS_TOP, "1" if always_on_top else "0")
    app_kv_set(
        conn,
        _K_GEOM,
        json.dumps(
            {"x": x, "y": y, "w": w, "h": h, "sn": screen_number},
            separators=(",", ":"),
        ),
    )


@dataclass(frozen=True)
class AppSettings:
    """User preferences stored under ``app_settings_v1`` (separate from panel shell keys)."""

    appearance_mode: str
    shortcuts_dir: Path | None
    grid_cols: int
    deck_show_hidden_items: bool
    ui_scale: float


def default_app_settings() -> AppSettings:
    return AppSettings(
        appearance_mode="dark",
        shortcuts_dir=None,
        grid_cols=DEFAULT_GRID_COLS,
        deck_show_hidden_items=False,
        ui_scale=UI_SCALE_DEFAULT,
    )


def clamp_grid_cols(n: int) -> int:
    return max(GRID_COLS_MIN, min(GRID_COLS_MAX, n))


def clamp_ui_scale(x: float) -> float:
    return max(UI_SCALE_MIN, min(UI_SCALE_MAX, float(x)))


# Preset labels for Settings (values must stay within ``clamp_ui_scale`` bounds).
UI_SCALE_PRESETS: tuple[tuple[str, float], ...] = (
    ("100%", 1.0),
    ("110%", 1.1),
    ("125%", 1.25),
    ("150%", 1.5),
)


def nearest_ui_scale_preset_value(x: float) -> float:
    """Pick the closest preset so the menu always reflects a valid choice."""
    x = clamp_ui_scale(x)
    return min((v for _, v in UI_SCALE_PRESETS), key=lambda p: abs(p - x))


def _parse_app_settings_dict(data: dict[str, Any]) -> AppSettings:
    base = default_app_settings()
    raw_am = data.get("appearance_mode")
    if isinstance(raw_am, str) and raw_am in _APPEARANCE_MODES:
        appearance_mode = raw_am
    else:
        appearance_mode = base.appearance_mode

    shortcuts_dir: Path | None = None
    raw_sd = data.get("shortcuts_dir")
    if isinstance(raw_sd, str) and raw_sd.strip():
        shortcuts_dir = Path(raw_sd)

    grid_cols = base.grid_cols
    raw_gc = data.get("grid_cols")
    if isinstance(raw_gc, bool):
        pass
    elif isinstance(raw_gc, int):
        grid_cols = clamp_grid_cols(raw_gc)
    elif isinstance(raw_gc, float):
        grid_cols = clamp_grid_cols(int(raw_gc))

    deck_show_hidden_items = base.deck_show_hidden_items
    raw_dh = data.get("deck_show_hidden_items")
    if raw_dh is True:
        deck_show_hidden_items = True
    elif raw_dh is False:
        deck_show_hidden_items = False

    ui_scale = base.ui_scale
    raw_us = data.get("ui_scale")
    if isinstance(raw_us, bool):
        pass
    elif isinstance(raw_us, (int, float)):
        try:
            ui_scale = clamp_ui_scale(float(raw_us))
        except (TypeError, ValueError, OverflowError):
            ui_scale = base.ui_scale

    return AppSettings(
        appearance_mode=appearance_mode,
        shortcuts_dir=shortcuts_dir,
        grid_cols=grid_cols,
        deck_show_hidden_items=deck_show_hidden_items,
        ui_scale=ui_scale,
    )


def load_app_settings(conn: sqlite3.Connection) -> AppSettings:
    raw = app_kv_get(conn, _K_APP_SETTINGS)
    if not raw:
        return default_app_settings()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return default_app_settings()
    if not isinstance(data, dict):
        return default_app_settings()
    return _parse_app_settings_dict(data)


def save_app_settings(conn: sqlite3.Connection, settings: AppSettings) -> None:
    sd: str | None = None
    if settings.shortcuts_dir is not None:
        sd = str(settings.shortcuts_dir)
    payload = {
        "appearance_mode": settings.appearance_mode,
        "shortcuts_dir": sd,
        "grid_cols": settings.grid_cols,
        "deck_show_hidden_items": settings.deck_show_hidden_items,
        "ui_scale": settings.ui_scale,
    }
    app_kv_set(
        conn,
        _K_APP_SETTINGS,
        json.dumps(payload, separators=(",", ":")),
    )


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
    clear_label_override: bool = False,
    icon_path: str | None = None,
    notes: str | None = None,
    clear_notes: bool = False,
    flags: dict[str, Any] | None = None,
    viewer_rect: tuple[int, int, int, int] | None = None,
    clear_viewer_rect: bool = False,
) -> bool:
    """Update deck row. Use ``clear_label_override`` / ``clear_notes`` for SQL NULL (default stem / no notes)."""
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
    if clear_label_override:
        new_label = None
    elif label_override is not None:
        new_label = label_override
    else:
        new_label = item.label_override
    new_icon = icon_path if icon_path is not None else item.icon_path
    if clear_notes:
        new_notes = None
    elif notes is not None:
        new_notes = notes
    else:
        new_notes = item.notes

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


def export_db_to_file(dest: Path, *, source: Path | None = None) -> None:
    """Copy the SQLite database to ``dest`` using the SQLite backup API (consistent snapshot)."""
    src_path = Path(source if source is not None else default_db_path())
    out = Path(dest).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    if not src_path.is_file():
        raise FileNotFoundError(str(src_path))
    resolved_src = src_path.resolve()
    resolved_out = out.resolve()
    if resolved_out == resolved_src:
        raise ValueError("Destination must differ from the source database path.")
    if out.exists():
        out.unlink()
    src_conn = sqlite3.connect(str(src_path))
    try:
        dst_conn = sqlite3.connect(str(out))
        try:
            src_conn.backup(dst_conn)
            dst_conn.commit()
        finally:
            dst_conn.close()
    finally:
        src_conn.close()


def merge_full_order_after_visible_reorder(
    full_ordered_ids: list[int],
    visible_new_order: list[int],
    *,
    visible_id_set: frozenset[int],
) -> list[int]:
    """Build a full id list for :func:`reorder_items` after the user reorders only deck-visible tiles.

    Walk ``full_ordered_ids`` in current library order. At each position, if that id is in
    ``visible_id_set``, substitute the next id from ``visible_new_order``; otherwise keep the
    hidden id in place. Preserves relative positions of non-visible items.

    ``visible_new_order`` must be a permutation of the visible ids (same set as
    ``full_ordered_ids`` ∩ ``visible_id_set``).
    """
    n_vis_slots = sum(1 for i in full_ordered_ids if i in visible_id_set)
    if len(visible_new_order) != n_vis_slots:
        raise ValueError("visible_new_order length must match visible slot count in full order")
    if frozenset(visible_new_order) != visible_id_set:
        raise ValueError("visible_new_order must contain exactly the visible id set")
    it_new = iter(visible_new_order)
    return [next(it_new) if i in visible_id_set else i for i in full_ordered_ids]


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


def item_hidden_from_deck(item: DeckItem) -> bool:
    return bool(parse_flags(item).get(FLAG_HIDE_FROM_DECK))


def list_deck_items(conn: sqlite3.Connection, settings: AppSettings) -> list[DeckItem]:
    """Deck grid items; omits ``hide_from_deck`` unless ``deck_show_hidden_items``."""
    all_items = list_items(conn)
    if settings.deck_show_hidden_items:
        return all_items
    return [it for it in all_items if not item_hidden_from_deck(it)]


def record_item_open(
    conn: sqlite3.Connection,
    *,
    item_id: int,
    source_path: str,
    kind: str = "view",
) -> None:
    opened_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO launch_events (item_id, source_path, opened_at, kind)
        VALUES (?, ?, ?, ?)
        """,
        (item_id, source_path, opened_at, kind),
    )
    conn.commit()
