"""Generate the GROW8 physical ER diagram and relational schema from the live database.

Reads tables, columns, keys and foreign keys from MySQL's information_schema, so the
diagram always matches db/init/001_schema.sql. Writes, next to this file:

    GROW8-ER-Diagram.svg            page 1: ER diagram (crow's foot)
    GROW8-Relational-Schema.svg     page 2: relational schema
    GROW8-ER-Diagram.pdf            both pages (needs rsvg-convert and pdfunite)

and docs/db/relational-schema.md.

Usage, with the stack up (`make up` in grow8-backend):
    pip install pymysql pillow
    MYSQL_PASSWORD=... python docs/diagrams/generate_er_diagram.py
Connection settings default to the dev database on localhost:3307 (see .env.example).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pymysql

HERE = Path(__file__).resolve().parent
DOCS_DB = HERE.parent / "db"
FONT = "Inter, 'DejaVu Sans', sans-serif"
W, H = 2120, 1660
HEADER_H, ROW_H, PAD_B = 28, 21, 6

try:  # exact text widths when Pillow and Inter are installed
    from PIL import ImageFont

    _FONTS: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}

    def text_width(s: str, size: float, bold: bool = False) -> float:
        key = (round(size * 10), bold)
        if key not in _FONTS:
            name = "Inter-SemiBold.otf" if bold else "Inter-Regular.otf"
            _FONTS[key] = ImageFont.truetype(f"/usr/share/fonts/opentype/inter/{name}", size)
        return _FONTS[key].getlength(s)

    text_width("x", 12)
except Exception:  # noqa: BLE001 - fall back to an average glyph width

    def text_width(s: str, size: float, bold: bool = False) -> float:
        return len(s) * size * (0.6 if bold else 0.56)


# --- groups, colours and layout -------------------------------------------------

GROUPS = [
    ("Identity and profiles", "#2563EB", ["user_account", "contributor_profile", "creator_organization"]),
    ("Reference data", "#7C3AED", ["opportunity_category", "skill", "badge"]),
    ("Opportunities and skills", "#059669", ["opportunity", "opportunity_skill", "contributor_skill"]),
    ("Applications and work", "#D97706", ["application", "work_submission", "submission_attachment"]),
    ("Verification and feedback", "#DC2626", ["work_verification", "feedback", "admin_review"]),
    ("Rewards", "#0891B2", ["contributor_badge", "point_transaction"]),
    ("Notifications", "#475569", ["notification"]),
]
COLOR = {t: c for _, c, ts in GROUPS for t in ts}

# table -> (x, y, width)
POS = {
    "creator_organization": (75, 166, 300),
    "opportunity": (498, 146, 304),
    "opportunity_category": (75, 696, 262),
    "notification": (933, 150, 272),
    "opportunity_skill": (933, 416, 212),
    "application": (933, 536, 250),
    "contributor_skill": (933, 816, 232),
    "skill": (1336, 376, 200),
    "work_submission": (1336, 515, 250),
    "feedback": (1336, 747, 250),
    "submission_attachment": (1707, 267, 262),
    "work_verification": (1707, 494, 300),
    "admin_review": (1707, 725, 280),
    "point_transaction": (1707, 1026, 262),
    "user_account": (75, 1110, 250),
    "contributor_profile": (498, 1110, 262),
    "contributor_badge": (933, 1110, 232),
    "badge": (933, 1246, 320),
}

BUS_Y = 985  # horizontal line carrying user_account keys to the right-hand tables

# constraint -> route. Lines start at the parent key and end at the FK column.
#   ("Z", parent_side, x, child_side)                      3 segments via channel x
#   ("U", parent_side, x1, y, x2, child_side)              5 segments via x1, y, x2
ROUTES = {
    "fk_creator_organization_owner": ("Z", "L", 40, "L"),
    "fk_notification_user": ("U", "L", 40, 100, 905, "L"),
    "fk_opportunity_organization": ("Z", "R", 436, "L"),
    "fk_opportunity_category": ("Z", "R", 410, "L"),
    "fk_opportunity_skill_opportunity": ("Z", "R", 860, "L"),
    "fk_application_opportunity": ("Z", "R", 860, "L"),
    "fk_notification_opportunity": ("U", "L", 470, 120, 880, "L"),
    "fk_opportunity_skill_skill": ("Z", "L", 1240, "R"),
    "fk_contributor_skill_skill": ("Z", "L", 1240, "R"),
    "fk_contributor_profile_user": ("Z", "R", 420, "L"),
    "fk_application_contributor": ("Z", "R", 885, "L"),
    "fk_contributor_skill_contributor": ("Z", "R", 885, "L"),
    "fk_contributor_badge_contributor": ("Z", "R", 885, "L"),
    "fk_point_transaction_contributor": ("Z", "R", 885, "L"),
    "fk_contributor_badge_badge": ("Z", "L", 912, "L"),
    "fk_point_transaction_contributor_badge": ("Z", "R", 1600, "L"),
    "fk_work_submission_application": ("Z", "R", 1270, "L"),
    "fk_feedback_application": ("Z", "R", 1270, "L"),
    "fk_feedback_author": ("U", "R", 440, BUS_Y, 1284, "L"),
    "fk_feedback_subject": ("U", "R", 440, BUS_Y, 1300, "L"),
    "fk_admin_review_admin": ("U", "R", 440, BUS_Y, 1665, "L"),
    "fk_work_verification_verified_by": ("U", "R", 440, BUS_Y, 2060, "R"),
    "fk_admin_review_feedback": ("Z", "R", 1650, "L"),
    "fk_submission_attachment_submission": ("Z", "R", 1640, "L"),
    "fk_work_verification_submission": ("Z", "R", 1640, "L"),
    "fk_point_transaction_verification": ("Z", "R", 2085, "R"),
}

VIEW_NOTES = {
    "v_contributor_verified_hours": "SUM(verified_hours) of approved work_verification rows",
    "v_user_rating": "AVG(rating) of feedback approved in admin_review",
    "v_feedback_status": "pending until an admin_review row exists",
    "v_leaderboard": "SUM(points) from point_transaction, RANK() OVER",
    "v_contributor_skill": "verified once approved work used the skill",
}


# --- schema --------------------------------------------------------------------


@dataclass
class Column:
    name: str
    type: str
    nullable: bool
    pk: bool = False
    fk: bool = False
    uk: bool = False


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)

    def row(self, column: str) -> int:
        return next(i for i, c in enumerate(self.columns) if c.name == column)


@dataclass
class ForeignKey:
    name: str
    table: str
    columns: list[str]
    ref_table: str
    ref_columns: list[str]


def short_type(column_type: str) -> str:
    t = column_type.upper().replace(" UNSIGNED", "")
    if t.startswith("ENUM"):
        return "ENUM"
    if t in ("TINYINT(1)",):
        return "BOOLEAN"
    return t.replace("INT(10)", "INT").replace("SMALLINT(5)", "SMALLINT")


def load_schema(conn: pymysql.Connection, db: str) -> tuple[dict[str, Table], list[ForeignKey], dict]:
    cur = conn.cursor()
    cur.execute(
        "SELECT c.table_name, c.column_name, c.column_type, c.is_nullable "
        "FROM information_schema.columns c JOIN information_schema.tables t "
        "  ON t.table_schema = c.table_schema AND t.table_name = c.table_name "
        "WHERE c.table_schema = %s AND t.table_type = 'BASE TABLE' "
        "ORDER BY c.table_name, c.ordinal_position",
        (db,),
    )
    tables: dict[str, Table] = {}
    for tname, cname, ctype, nullable in cur.fetchall():
        tables.setdefault(tname, Table(tname)).columns.append(
            Column(cname, short_type(ctype), nullable == "YES")
        )
    cur.execute(
        "SELECT tc.table_name, tc.constraint_type, k.column_name, tc.constraint_name "
        "FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage k "
        "  ON k.constraint_schema = tc.constraint_schema AND k.constraint_name = tc.constraint_name "
        " AND k.table_name = tc.table_name "
        "WHERE tc.table_schema = %s AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE', 'FOREIGN KEY')",
        (db,),
    )
    unique_sets: dict[tuple[str, str], list[str]] = {}
    for tname, ctype, cname, constraint in cur.fetchall():
        col = next(c for c in tables[tname].columns if c.name == cname)
        if ctype == "PRIMARY KEY":
            col.pk = True
            unique_sets.setdefault((tname, "PRIMARY"), []).append(cname)
        elif ctype == "FOREIGN KEY":
            col.fk = True
        else:
            unique_sets.setdefault((tname, constraint), []).append(cname)
    for (tname, constraint), cols in unique_sets.items():
        if constraint != "PRIMARY" and len(cols) == 1:
            next(c for c in tables[tname].columns if c.name == cols[0]).uk = True
    cur.execute(
        "SELECT constraint_name, table_name, GROUP_CONCAT(column_name ORDER BY ordinal_position), "
        "       referenced_table_name, GROUP_CONCAT(referenced_column_name ORDER BY ordinal_position) "
        "FROM information_schema.key_column_usage "
        "WHERE table_schema = %s AND referenced_table_name IS NOT NULL "
        "GROUP BY constraint_name, table_name, referenced_table_name ORDER BY table_name, constraint_name",
        (db,),
    )
    fks = [ForeignKey(n, t, c.split(","), rt, rc.split(",")) for n, t, c, rt, rc in cur.fetchall()]
    stats = {}
    for key, sql in {
        "triggers": "SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = %s",
        "views": "SELECT COUNT(*) FROM information_schema.views WHERE table_schema = %s",
    }.items():
        cur.execute(sql, (db,))
        stats[key] = cur.fetchone()[0]
    cur.execute(
        "SELECT table_name FROM information_schema.views WHERE table_schema = %s ORDER BY table_name",
        (db,),
    )
    stats["view_names"] = [r[0] for r in cur.fetchall()]
    stats["unique_sets"] = unique_sets
    return tables, fks, stats


def is_unique(stats: dict, table: str, cols: list[str]) -> bool:
    return any(t == table and sorted(c) == sorted(cols) for (t, _), c in stats["unique_sets"].items())


# --- drawing helpers -------------------------------------------------------------


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=12, weight=400, color="#334155", anchor="start", italic=False) -> str:
    style = ' font-style="italic"' if italic else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{style}>{esc(s)}</text>'
    )


def row_y(table: str, row: int) -> float:
    return POS[table][1] + HEADER_H + row * ROW_H + ROW_H / 2


def side_x(table: str, side: str) -> float:
    x, _, w = POS[table]
    return x if side == "L" else x + w


def chip(x, y, label) -> str:
    fill, ink = {"PK": ("#FDE68A", "#92400E"), "FK": ("#DBEAFE", "#1E40AF"), "UK": ("#EDE9FE", "#5B21B6")}[label]
    return (
        f'<rect x="{x}" y="{y - 6.5:.1f}" width="20" height="13" rx="3" fill="{fill}"/>'
        + text(x + 10, y + 3.2, label, 8, 700, ink, "middle")
    )


def fit_widths(tables: dict[str, Table]) -> None:
    """Widen a table when its longest name + type + null marker would not fit."""
    for t in tables.values():
        x, y, w = POS[t.name]
        names = max(text_width(c.name, 12, c.pk) for c in t.columns)
        types = max(text_width(c.type, 11) for c in t.columns)
        need = 58 + names + 16 + types + 38
        if need > w:
            POS[t.name] = (x, y, round(need))


def draw_table(t: Table) -> str:
    x, y, w = POS[t.name]
    h = HEADER_H + len(t.columns) * ROW_H + PAD_B
    c = COLOR[t.name]
    out = [
        f'<rect x="{x + 2}" y="{y + 3}" width="{w}" height="{h}" rx="6" fill="#0F172A" opacity="0.06"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#FFFFFF" stroke="{c}" stroke-width="1.6"/>',
        f'<path d="M{x},{y + HEADER_H} v-{HEADER_H - 6} a6,6 0 0 1 6,-6 h{w - 12} a6,6 0 0 1 6,6 '
        f'v{HEADER_H - 6} z" fill="{c}"/>',
        text(x + 10, y + 18.5, t.name, 13, 700, "#FFFFFF"),
    ]
    name_x = x + 58
    type_x = name_x + max(text_width(col.name, 12, col.pk) for col in t.columns) + 16
    for i, col in enumerate(t.columns):
        cy = row_y(t.name, i)
        if col.pk:
            out.append(f'<rect x="{x + 1}" y="{cy - ROW_H / 2:.1f}" width="{w - 2}" height="{ROW_H}" fill="#FFFBEB"/>')
        badges = [b for b, on in (("PK", col.pk), ("FK", col.fk), ("UK", col.uk and not col.pk)) if on]
        for j, b in enumerate(badges[:2]):
            out.append(chip(x + 8 + j * 23, cy, b))
        out.append(text(name_x, cy + 4.3, col.name, 12, 600 if col.pk else 400, "#0F172A"))
        out.append(text(type_x, cy + 4.3, col.type, 11, 400, "#64748B"))
        if col.nullable:
            out.append(text(x + w - 9, cy + 4, "null", 10, 400, "#94A3B8", "end", italic=True))
    return "\n".join(out)


def symbol(px, py, direction, kind, color) -> str:
    """Crow's-foot end marker at (px, py); direction is +1 if the line leaves to the right."""
    d = direction
    s = f'stroke="{color}" stroke-width="1.6" fill="none"'
    bar = lambda off: f'<line x1="{px + d * off}" y1="{py - 8}" x2="{px + d * off}" y2="{py + 8}" {s}/>'  # noqa: E731
    circle = lambda off: (  # noqa: E731
        f'<circle cx="{px + d * off}" cy="{py}" r="4.5" fill="#FFFFFF" stroke="{color}" stroke-width="1.6"/>'
    )
    if kind == "exactly_one":
        return bar(7) + bar(12)
    if kind == "zero_or_one":
        return bar(7) + circle(17)
    # zero or many: crow's foot touching the table, circle behind it
    foot = (
        f'<path d="M{px},{py - 7} L{px + d * 11},{py} L{px},{py + 7}" {s}/>'
        f'<line x1="{px}" y1="{py}" x2="{px + d * 11}" y2="{py}" {s}/>'
    )
    return foot + circle(18)


@dataclass
class Edge:
    fk: ForeignKey
    points: list[tuple[float, float]]
    color: str
    parent_kind: str
    child_kind: str
    parent_dir: int
    child_dir: int


def build_edges(tables, fks, stats) -> list[Edge]:
    edges = []
    for fk in fks:
        route = ROUTES[fk.name]
        parent, child = fk.ref_table, fk.table
        # composite keys anchor on their last column (the one that identifies the pair)
        prow = tables[parent].row(fk.ref_columns[-1])
        crow = tables[child].row(fk.columns[-1])
        p_side, c_side = route[1], route[-1]
        p = (side_x(parent, p_side), row_y(parent, prow))
        c = (side_x(child, c_side), row_y(child, crow))
        if route[0] == "Z":
            x = route[2]
            pts = [p, (x, p[1]), (x, c[1]), c]
        else:
            _, _, x1, y, x2, _ = route
            pts = [p, (x1, p[1]), (x1, y), (x2, y), (x2, c[1]), c]
        # drop points where the line does not actually turn (straight runs)
        pts = [q for i, q in enumerate(pts)
               if i in (0, len(pts) - 1)
               or not ((pts[i - 1][0] == q[0] == pts[i + 1][0]) or (pts[i - 1][1] == q[1] == pts[i + 1][1]))]
        nullable = any(next(col for col in tables[child].columns if col.name == n).nullable for n in fk.columns)
        unique = is_unique(stats, child, fk.columns)
        edges.append(
            Edge(
                fk,
                pts,
                COLOR[parent],
                "zero_or_one" if nullable else "exactly_one",
                "zero_or_one" if unique else "zero_or_many",
                -1 if p_side == "L" else 1,
                -1 if c_side == "L" else 1,
            )
        )
    return edges


def segments(edge: Edge):
    pts = [(round(x, 1), round(y, 1)) for x, y in edge.points]
    return [(a, b) for a, b in zip(pts, pts[1:], strict=False) if a != b]


def draw_edges(edges: list[Edge]) -> str:
    vertical = []  # (x, y0, y1, parent_key)
    for e in edges:
        key = (e.fk.ref_table, tuple(e.fk.ref_columns))
        for (x0, y0), (x1, y1) in segments(e):
            if x0 == x1:
                vertical.append((x0, min(y0, y1), max(y0, y1), key))
    out, dots = [], set()
    for e in edges:
        key = (e.fk.ref_table, tuple(e.fk.ref_columns))
        d = []
        for (x0, y0), (x1, y1) in segments(e):
            if not d:
                d.append(f"M{x0},{y0}")
            if y0 == y1:  # horizontal: hop over vertical lines of other parents
                step = 1 if x1 > x0 else -1
                hops = sorted(
                    (vx for vx, vy0, vy1, vkey in vertical
                     if vkey != key and vy0 < y0 < vy1 and min(x0, x1) + 8 < vx < max(x0, x1) - 8),
                    reverse=step < 0,
                )
                for vx in hops:
                    d.append(f"L{vx - step * 6},{y0} A6,6 0 0 {1 if step > 0 else 0} {vx + step * 6},{y0}")
            d.append(f"L{x1},{y1}")
        out.append(f'<path d="{" ".join(d)}" fill="none" stroke="{e.color}" stroke-width="1.6"/>')
        # a dot where this line leaves a trunk it shares with another line from the same key
        for other in edges:
            if other is e or (other.fk.ref_table, tuple(other.fk.ref_columns)) != key:
                continue
            for (ax, ay), (bx, by) in segments(other):
                for tx, ty in e.points[1:-1]:
                    if ax == bx == tx and min(ay, by) < ty < max(ay, by):
                        dots.add((tx, ty))
                    if ay == by == ty and min(ax, bx) < tx < max(ax, bx):
                        dots.add((tx, ty))
        out.append(symbol(*e.points[0], e.parent_dir, e.parent_kind, e.color))
        out.append(symbol(*e.points[-1], e.child_dir, e.child_kind, e.color))
    for x, y in sorted(dots):
        out.append(f'<circle cx="{x}" cy="{y}" r="3.4" fill="#334155"/>')
    return "\n".join(out)


def draw_legend(stats) -> str:
    ly = 1440
    out = [f'<line x1="40" y1="{ly}" x2="{W - 40}" y2="{ly}" stroke="#E2E8F0" stroke-width="1.2"/>']
    h1 = lambda x, s: text(x, ly + 30, s, 13, 700, "#0F172A")  # noqa: E731
    lx = 40
    out.append(h1(lx, "Cardinality (crow's foot)"))
    for i, (kind, label, note) in enumerate(
        [
            ("exactly_one", "Exactly one", "parent side, FK is NOT NULL"),
            ("zero_or_one", "Zero or one", "parent side if FK is nullable; child side if FK is UNIQUE"),
            ("zero_or_many", "Zero or many", "child side of an ordinary FK"),
        ]
    ):
        yy = ly + 58 + i * 30
        out.append(f'<line x1="{lx}" y1="{yy}" x2="{lx + 56}" y2="{yy}" stroke="#334155" stroke-width="1.6"/>')
        out.append(f'<rect x="{lx + 56}" y="{yy - 10}" width="4" height="20" fill="#334155"/>')
        out.append(symbol(lx + 56, yy, -1, kind, "#334155"))
        out.append(text(lx + 74, yy + 4.5, label, 12, 600, "#0F172A"))
        out.append(text(lx + 162, yy + 4.5, note, 12, 400, "#475569"))
    yy = ly + 150
    out.append(
        f'<path d="M{lx},{yy} L{lx + 22},{yy} A7,7 0 0 1 {lx + 36},{yy} L{lx + 58},{yy}" fill="none" '
        f'stroke="#334155" stroke-width="1.6"/><line x1="{lx + 29}" y1="{yy - 12}" x2="{lx + 29}" '
        f'y2="{yy + 12}" stroke="#94A3B8" stroke-width="1.6"/>'
    )
    out.append(text(lx + 70, yy + 4.5, "Hop", 12, 600, "#0F172A"))
    out.append(text(lx + 104, yy + 4.5, "lines cross, not connected", 12, 400, "#475569"))
    out.append(
        f'<line x1="{lx + 300}" y1="{yy}" x2="{lx + 356}" y2="{yy}" stroke="#334155" stroke-width="1.6"/>'
        f'<line x1="{lx + 328}" y1="{yy}" x2="{lx + 328}" y2="{yy + 14}" stroke="#334155" stroke-width="1.6"/>'
        f'<circle cx="{lx + 328}" cy="{yy}" r="3.4" fill="#334155"/>'
    )
    out.append(text(lx + 368, yy + 4.5, "Branch", 12, 600, "#0F172A"))
    out.append(text(lx + 420, yy + 4.5, "one key, several tables", 12, 400, "#475569"))

    lx = 640
    out.append(h1(lx, "Columns"))
    for i, (b, label) in enumerate([("PK", "Primary key"), ("FK", "Foreign key"), ("UK", "Unique key")]):
        yy = ly + 58 + i * 26
        out.append(chip(lx, yy, b))
        out.append(text(lx + 32, yy + 4.3, label))
    out.append(text(lx, ly + 140, "null", 10, 400, "#94A3B8", italic=True))
    out.append(text(lx + 32, ly + 140, "Nullable (every other column is NOT NULL)"))
    out.append(text(lx, ly + 166, "INT = INT UNSIGNED · DATETIME in UTC · BOOLEAN = TINYINT(1)", 11.5, 400, "#64748B"))
    out.append(text(lx, ly + 184, "Lines run from the parent key to the exact FK column.", 11.5, 400, "#64748B"))
    out.append(text(lx, ly + 202, "point_transaction → contributor_badge is the composite key (contributor_id, badge_id).", 11.5, 400, "#64748B"))

    lx = 1180
    out.append(h1(lx, "Table groups (line colour = parent group)"))
    for i, (name, color, _) in enumerate(GROUPS):
        col, row = (0, i) if i < 4 else (1, i - 4)
        x, yy = lx + col * 210, ly + 58 + row * 26
        out.append(f'<rect x="{x}" y="{yy - 7}" width="14" height="14" rx="3" fill="{color}"/>')
        out.append(text(x + 22, yy + 4.3, name))

    lx = 1640
    out.append(h1(lx, "Derived values: views, never stored"))
    for i, view in enumerate(stats["view_names"]):
        yy = ly + 56 + i * 32
        out.append(text(lx, yy, view, 12, 600, "#0F172A"))
        out.append(text(lx, yy + 15, VIEW_NOTES.get(view, ""), 11, 400, "#64748B"))
    return "\n".join(out)


def er_svg(tables, fks, stats) -> str:
    n_cols = sum(len(t.columns) for t in tables.values())
    sub = (
        f"MySQL 8.4 · {len(tables)} tables · {n_cols} columns · {len(fks)} foreign keys · "
        f"{stats['triggers']} integrity triggers · {stats['views']} derived-value views · all tables in BCNF"
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        text(40, 48, "GROW8 — Entity-Relationship Diagram", 30, 800, "#0F172A"),
        text(40, 74, sub, 13.5, 400, "#475569"),
        text(W - 40, 46, "ENSF 608 · Group 2", 14, 700, "#0F172A", "end"),
        text(W - 40, 70, f"Generated from db/init/001_schema.sql · {date.today():%b %-d, %Y}", 12, 400, "#64748B", "end"),
        f'<line x1="40" y1="88" x2="{W - 40}" y2="88" stroke="#E2E8F0" stroke-width="1.2"/>',
    ]
    edges = build_edges(tables, fks, stats)
    parts.append(draw_edges(edges))
    parts += [draw_table(tables[name]) for name in POS]
    parts.append(draw_legend(stats))
    parts.append("</svg>")
    return "\n".join(parts)


# --- relational schema -------------------------------------------------------------


def schema_svg(tables, fks, stats) -> str:
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        text(40, 48, "GROW8 — Relational Schema", 30, 800, "#0F172A"),
        text(40, 74, "Primary keys underlined · foreign keys in blue italics, each listed under its relation "
             "as columns → relation(key) · all relations in BCNF", 13.5, 400, "#475569"),
        text(W - 40, 46, "ENSF 608 · Group 2", 14, 700, "#0F172A", "end"),
        text(W - 40, 70, f"Generated from db/init/001_schema.sql · {date.today():%b %-d, %Y}", 12, 400, "#64748B", "end"),
        f'<line x1="40" y1="88" x2="{W - 40}" y2="88" stroke="#E2E8F0" stroke-width="1.2"/>',
    ]
    size, line_h, ref_h = 15, 25, 21
    col_w = (W - 80 - 2 * 40) / 3
    columns = [GROUPS[0:2], GROUPS[2:4], GROUPS[4:7]]
    for ci, groups in enumerate(columns):
        x = 40 + ci * (col_w + 40)
        y = 132
        for gname, color, names in groups:
            out.append(f'<rect x="{x}" y="{y - 15}" width="12" height="12" rx="3" fill="{color}"/>')
            out.append(text(x + 20, y - 4, gname.upper(), 12, 700, color))
            y += 30
            for name in names:
                t = tables[name]
                tokens = [(c.name, c.pk, c.fk) for c in t.columns]
                # lay out "name(a, b, c)" with wrapping
                cx = x + text_width(name + "(", size, True)
                out.append(text(x, y, name, size, 700, "#0F172A"))
                out.append(text(x + text_width(name, size, True), y, "(", size, 400, "#0F172A"))
                for i, (cname, pk, fk) in enumerate(tokens):
                    punct = ", " if i < len(tokens) - 1 else ")"
                    wname = text_width(cname, size, pk)
                    if cx + wname + text_width(punct, size) > x + col_w:
                        y += line_h
                        cx = x + 28
                    out.append(text(cx, y, cname, size, 700 if pk else 400,
                                    "#1E40AF" if fk else "#0F172A", italic=fk))
                    if pk:
                        out.append(f'<line x1="{cx:.1f}" y1="{y + 3.5:.1f}" x2="{cx + wname:.1f}" '
                                   f'y2="{y + 3.5:.1f}" stroke="{"#1E40AF" if fk else "#0F172A"}" stroke-width="1.3"/>')
                    out.append(text(cx + wname, y, punct, size, 400, "#0F172A"))
                    cx += wname + text_width(punct, size)
                y += ref_h + 2
                for fk in fks:
                    if fk.table == name:
                        out.append(text(x + 28, y, f"{', '.join(fk.columns)} → {fk.ref_table}"
                                        f"({', '.join(fk.ref_columns)})", 12.5, 400, "#475569"))
                        y += ref_h
                y += 18
            y += 10
        if ci == 2:
            out.append(f'<line x1="{x}" y1="{y - 8}" x2="{x + col_w}" y2="{y - 8}" stroke="#E2E8F0" stroke-width="1.2"/>')
            y += 22
            out.append(text(x, y, "VIEWS (DERIVED, NOT STORED)", 12, 700, "#0F172A"))
            y += 28
            for v in stats["view_names"]:
                out.append(text(x, y, v, 14, 600, "#0F172A"))
                out.append(text(x + 28, y + 19, VIEW_NOTES.get(v, ""), 12.5, 400, "#64748B"))
                y += 44
    out.append("</svg>")
    return "\n".join(out)


def schema_markdown(tables, fks, stats) -> str:
    n_cols = sum(len(t.columns) for t in tables.values())
    md = [
        "# Relational Schema — Grow8 Database",
        "",
        "**ENSF 608 · Group 2** · Normalization & relationship validation — Vineeth Donthamsetty",
        "",
        f"> Generated {date.today():%b %-d, %Y} from the loaded schema (`grow8-backend/db/init/001_schema.sql`) by "
        f"`docs/diagrams/generate_er_diagram.py`: {len(tables)} relations, {n_cols} attributes, {len(fks)} foreign keys. "
        "The same schema is drawn as an ER diagram in `docs/diagrams/GROW8-ER-Diagram.pdf` (page 1) and as this "
        "notation on page 2.",
        "",
        "Notation: primary-key attributes are <ins>underlined</ins>, foreign-key attributes are *in italics*, and each "
        "foreign key is listed under its relation as `columns → relation(key)`. Types, nullability and meanings are in "
        "`data-dictionary.md`; functional dependencies and the BCNF check are in `functional-dependencies.md`.",
        "",
    ]
    for g, _, names in GROUPS:
        md += [f"## {g}", ""]
        for name in names:
            t = tables[name]
            attrs = []
            for c in t.columns:
                if c.pk and c.fk:
                    attrs.append(f"<ins>*{c.name}*</ins>")
                elif c.pk:
                    attrs.append(f"<ins>{c.name}</ins>")
                elif c.fk:
                    attrs.append(f"*{c.name}*")
                else:
                    attrs.append(c.name)
            md.append(f"**{name}**({', '.join(attrs)})")
            md.append("")
            for fk in fks:
                if fk.table == name:
                    md.append(f"- FK `{', '.join(fk.columns)}` → `{fk.ref_table}({', '.join(fk.ref_columns)})`")
            uniques = [
                cols for (tn, cname), cols in stats["unique_sets"].items()
                if tn == name and cname != "PRIMARY"
            ]
            for cols in uniques:
                md.append(f"- Candidate key `({', '.join(cols)})`")
            md.append("")
    md += ["## Views (derived, not stored)", ""]
    for v in stats["view_names"]:
        md.append(f"- `{v}`: {VIEW_NOTES.get(v, '')}")
    md.append("")
    return "\n".join(md)


def main() -> None:
    db = os.environ.get("MYSQL_DATABASE", "grow8")
    conn = pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3307")),
        user=os.environ.get("MYSQL_USER", "grow8"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=db,
    )
    tables, fks, stats = load_schema(conn, db)
    fit_widths(tables)
    missing = set(tables) ^ set(POS)
    if missing or set(ROUTES) != {fk.name for fk in fks}:
        raise SystemExit(f"Layout out of date: tables {sorted(missing)}, routes "
                         f"{sorted(set(ROUTES) ^ {fk.name for fk in fks})}. Add them to POS / ROUTES.")
    (HERE / "GROW8-ER-Diagram.svg").write_text(er_svg(tables, fks, stats), encoding="utf-8")
    (HERE / "GROW8-Relational-Schema.svg").write_text(schema_svg(tables, fks, stats), encoding="utf-8")
    (DOCS_DB / "relational-schema.md").write_text(schema_markdown(tables, fks, stats), encoding="utf-8")
    if shutil.which("rsvg-convert") and shutil.which("pdfunite"):
        pages = []
        for name in ("GROW8-ER-Diagram", "GROW8-Relational-Schema"):
            pdf = HERE / f".{name}.pdf"
            subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(pdf), str(HERE / f"{name}.svg")], check=True)
            pages.append(str(pdf))
        subprocess.run(["pdfunite", *pages, str(HERE / "GROW8-ER-Diagram.pdf")], check=True)
        for p in pages:
            Path(p).unlink()
    print(f"{len(tables)} tables, {len(fks)} foreign keys, {stats['triggers']} triggers, {stats['views']} views")


if __name__ == "__main__":
    main()
