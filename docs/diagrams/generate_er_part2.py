"""Builds ER-diagram-part2-reports.drawio.svg: Part 2 of the conceptual ERD.

Part 1 (ER-diagram.drawio.svg) predates opportunity reports (ADR 0016, Nov 22).
Adding them there would need lines across the whole diagram, so they are drawn
here with the three Part 1 entities they relate to (dashed outlines).

The output is a draw.io file: it opens and edits in draw.io / diagrams.net like
Part 1, and also displays as a plain SVG. Every shape is defined once below and
written to both the draw.io model and the SVG picture, so the two always match.

    python3 docs/diagrams/generate_er_part2.py
"""

from html import escape
from pathlib import Path

OUT = Path(__file__).with_name("ER-diagram-part2-reports.drawio.svg")
W, H = 1660, 760
FONT = "Helvetica, Arial, sans-serif"
NAVY = "#14273C"

ENT_W, ENT_H = 236, 53
REL_W, REL_H = 182, 64
ATT_H = 28

nodes = {}  # id -> dict(kind, x, y, w, h, label, ...)
edges = []  # (id, src, dst, points, label_near_src, label_near_dst)


def entity(nid, label, x, y, reference=False):
    nodes[nid] = dict(kind="entity", label=label, x=x, y=y, w=ENT_W, h=ENT_H, ref=reference)


def relationship(nid, label, cx, cy):
    nodes[nid] = dict(kind="rel", label=label, x=cx - REL_W / 2, y=cy - REL_H / 2, w=REL_W, h=REL_H)


def attribute(nid, label, cx, cy, key=False, derived=False):
    w = max(100, 8.2 * len(label) + 28)
    nodes[nid] = dict(
        kind="attr",
        label=label,
        x=cx - w / 2,
        y=cy - ATT_H / 2,
        w=w,
        h=ATT_H,
        key=key,
        derived=derived,
    )


def center(n):
    return n["x"] + n["w"] / 2, n["y"] + n["h"] / 2


# --- entities -----------------------------------------------------------------
entity("contributor", "Contributor", 40, 250, reference=True)
entity("report", "Opportunity Report", 650, 250)
entity("opportunity", "Opportunity", 1380, 250, reference=True)
entity("review", "Report Review", 650, 540)
entity("admin", "Admin", 40, 540, reference=True)

# --- relationships --------------------------------------------------------------
relationship("submits", "SUBMITS", 470, 276.5)
relationship("flags", "FLAGS", 1110, 276.5)
relationship("decided", "HAS DECISION", 768, 420)
relationship("decides", "DECIDES", 470, 566.5)

# --- attributes -----------------------------------------------------------------
for i, (label, key, derived) in enumerate(
    [
        ("Report ID", True, False),
        ("Reason", False, False),
        ("Details", False, False),
        ("Created At", False, False),
        ("Status", False, True),
    ]
):
    attribute(f"ra{i}", label, 528 + i * 120, 120, key=key, derived=derived)
for i, (label, key) in enumerate(
    [
        ("Review ID", True),
        ("Decision", False),
        ("Reason", False),
        ("Reviewed At", False),
    ]
):
    attribute(f"va{i}", label, 588 + i * 120, 690, key=key)
attribute("taken", "Taken Down", 1498, 150, derived=True)


# --- relationship lines (label next to the entity end, as in Part 1) -------------
def link(eid, a, b, near_a, near_b):
    edges.append((eid, a, b, near_a, near_b))


link("e1", "contributor", "submits", "1..1", None)
link("e2", "report", "submits", "0..N", None)
link("e3", "report", "flags", "0..N", None)
link("e4", "opportunity", "flags", "1..1", None)
link("e5", "report", "decided", "1..1", None)
link("e6", "review", "decided", "0..1", None)
link("e7", "admin", "decides", "1..1", None)
link("e8", "review", "decides", "0..N", None)


def anchor(n, toward):
    """Point on n's border facing the other node (lines here are horizontal or vertical)."""
    cx, cy = center(n)
    tx, ty = toward
    if abs(tx - cx) >= abs(ty - cy):
        return (n["x"] + n["w"], cy) if tx > cx else (n["x"], cy)
    return (cx, n["y"] + n["h"]) if ty > cy else (cx, n["y"])


segments = []  # (x1, y1, x2, y2, edge_id)
labels = []  # (x, y, text, parent_edge)
for eid, a, b, near_a, _ in edges:
    na, nb = nodes[a], nodes[b]
    p1 = anchor(na, center(nb))
    p2 = anchor(nb, center(na))
    segments.append((*p1, *p2, eid))
    if near_a:
        # 26% of the way from the entity, lifted off the line like Part 1's labels
        lx = p1[0] + (p2[0] - p1[0]) * 0.26
        ly = p1[1] + (p2[1] - p1[1]) * 0.26
        if p1[1] == p2[1]:
            ly -= 18.6
        else:
            lx += 26
        labels.append((lx, ly, near_a, eid))

# attribute stems: entity edge -> bar -> each attribute
stems = []


def bracket(entity_id, attr_ids, bar_y):
    n = nodes[entity_id]
    cx = n["x"] + n["w"] / 2
    edge_y = n["y"] if bar_y < n["y"] else n["y"] + n["h"]
    for aid in attr_ids:
        a = nodes[aid]
        ax = a["x"] + a["w"] / 2
        ay = a["y"] + a["h"] if bar_y < n["y"] else a["y"]
        stems.append([(cx, edge_y), (cx, bar_y), (ax, bar_y), (ax, ay)])


bracket("report", [f"ra{i}" for i in range(5)], 190)
bracket("review", [f"va{i}" for i in range(4)], 640)
bracket("opportunity", ["taken"], 210)

NOTE = [
    "Part 2 of the GROW8 conceptual ERD: opportunity reports and takedown (ADR 0016).",
    "Dashed boxes: entities defined in Part 1 (ER-diagram.drawio.svg).",
    "Dashed ellipses: derived attributes, never stored.",
    "Status: pending until the report has a Report Review.",
    "Taken Down: the opportunity is cancelled and has an upheld report.",
    "A contributor reports an opportunity at most once; each report is decided once.",
]


# --- SVG picture --------------------------------------------------------------------
def svg_text(x, y, text, size, bold=False, underline=False, color="#000000", anchor="middle"):
    deco = ' text-decoration="underline"' if underline else ""
    weight = ' font-weight="bold"' if bold else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}"{weight}{deco} '
        f'fill="{color}" text-anchor="{anchor}" dominant-baseline="central">{escape(text)}</text>'
    )


parts = [
    f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>',
    svg_text(
        40,
        40,
        "GROW8 Conceptual ERD — Part 2: Opportunity reports and takedown",
        24,
        bold=True,
        anchor="start",
    ),
]
for x1, y1, x2, y2, _ in segments:
    parts.append(
        f'<path d="M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}" '
        'fill="none" stroke="#000000" stroke-width="1.63"/>'
    )
for pts in stems:
    d = " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    parts.append(f'<path d="M {d}" fill="none" stroke="#000000" stroke-width="1.63"/>')
for nid, n in nodes.items():
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]
    cx, cy = center(n)
    if n["kind"] == "entity":
        dash = ' stroke-dasharray="8 4"' if n["ref"] else ""
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="#ffffff" stroke="#000000"{dash}/>'
        )
        parts.append(svg_text(cx, cy, n["label"], 19.6, bold=True))
    elif n["kind"] == "rel":
        parts.append(
            f'<path d="M {cx:.1f} {y:.1f} L {x + w:.1f} {cy:.1f} L {cx:.1f} {y + h:.1f} '
            f'L {x:.1f} {cy:.1f} Z" fill="#ffffff" stroke="#000000"/>'
        )
        parts.append(svg_text(cx, cy, n["label"], 15.4, bold=True))
    else:
        dash = ' stroke-dasharray="4 2"' if n["derived"] else ""
        parts.append(
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w / 2:.1f}" ry="{h / 2:.1f}" '
            f'fill="#ffffff" stroke="#000000"{dash}/>'
        )
        parts.append(svg_text(cx, cy, n["label"], 14, underline=n["key"]))
for lx, ly, text, _ in labels:
    parts.append(
        f'<rect x="{lx - 17:.1f}" y="{ly - 10:.1f}" width="34" height="20" fill="#ffffff"/>'
    )
    parts.append(svg_text(lx, ly, text, 15.4, bold=True, color=NAVY))
note_x, note_y = 1040, 470
parts.append(
    f'<rect x="{note_x}" y="{note_y}" width="590" height="{28 + 26 * len(NOTE)}" '
    f'fill="#f7f7f7" stroke="#999999"/>'
)
for i, line in enumerate(NOTE):
    parts.append(
        svg_text(note_x + 16, note_y + 26 + 26 * i, line, 14, bold=(i == 0), anchor="start")
    )


# --- draw.io model -------------------------------------------------------------------
ENTITY = "rounded=0;html=1;whiteSpace=wrap;fontStyle=1;fontSize=19.6;"
REL = "rhombus;html=1;whiteSpace=wrap;fontSize=15.4;fontStyle=1;"
EDGE = "edgeStyle=none;rounded=0;html=1;endArrow=none;startArrow=none;strokeWidth=1.625;"
LABEL = (
    "edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];"
    f"fontColor={NAVY};fontSize=15.4;fontStyle=1;labelBackgroundColor=#FFFFFF;"
)

cells = ['<mxCell id="0" />', '<mxCell id="1" parent="0" />']


def geometry(n):
    return (
        f'<mxGeometry x="{n["x"]:.2f}" y="{n["y"]:.2f}" width="{n["w"]:.2f}" '
        f'height="{n["h"]:.2f}" as="geometry" />'
    )


cells.append(
    '<mxCell id="title" parent="1" style="text;html=1;fontSize=24;fontStyle=1;align=left;" '
    'value="GROW8 Conceptual ERD — Part 2: Opportunity reports and takedown" vertex="1">'
    '<mxGeometry x="40" y="22" width="900" height="36" as="geometry" /></mxCell>'
)
for nid, n in nodes.items():
    if n["kind"] == "entity":
        style = ENTITY + ("dashed=1;dashPattern=8 4;" if n["ref"] else "")
    elif n["kind"] == "rel":
        style = REL
    else:
        style = "ellipse;html=1;whiteSpace=wrap;fontSize=14;"
        style += "fontStyle=4;" if n["key"] else ""
        style += "dashed=1;dashPattern=4 2;" if n["derived"] else ""
    cells.append(
        f'<mxCell id="{nid}" parent="1" style="{style}" value="{escape(n["label"])}" '
        f'vertex="1">{geometry(n)}</mxCell>'
    )
for x1, y1, x2, y2, eid in segments:
    src = next(e for e in edges if e[0] == eid)
    cells.append(
        f'<mxCell id="{eid}" edge="1" parent="1" source="{src[1]}" target="{src[2]}" '
        f'style="{EDGE}"><mxGeometry relative="1" as="geometry" /></mxCell>'
    )
for i, (lx, ly, text, eid) in enumerate(labels):
    cells.append(
        f'<mxCell id="{eid}l" parent="1" style="text;html=1;align=center;'
        f"verticalAlign=middle;fontColor={NAVY};fontSize=15.4;fontStyle=1;"
        f'labelBackgroundColor=#FFFFFF;" value="{text}" vertex="1">'
        f'<mxGeometry x="{lx - 20:.2f}" y="{ly - 11:.2f}" width="40" height="22" '
        f'as="geometry" /></mxCell>'
    )
for i, pts in enumerate(stems):
    (sx, sy), (tx, ty) = pts[0], pts[-1]
    waypoints = "".join(f'<mxPoint x="{x:.2f}" y="{y:.2f}" />' for x, y in pts[1:-1])
    cells.append(
        f'<mxCell id="s{i}" edge="1" parent="1" style="{EDGE}">'
        f'<mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{sx:.2f}" y="{sy:.2f}" as="sourcePoint" />'
        f'<mxPoint x="{tx:.2f}" y="{ty:.2f}" as="targetPoint" />'
        f'<Array as="points">{waypoints}</Array></mxGeometry></mxCell>'
    )
note_html = "<br>".join(escape(line) for line in NOTE)
cells.append(
    f'<mxCell id="note" parent="1" style="rounded=0;html=1;whiteSpace=wrap;align=left;'
    f"verticalAlign=top;spacingLeft=14;spacingTop=8;fontSize=14;fillColor=#f7f7f7;"
    f'strokeColor=#999999;" value="{escape(note_html)}" vertex="1">'
    f'<mxGeometry x="{note_x}" y="{note_y}" width="590" height="{28 + 26 * len(NOTE)}" '
    f'as="geometry" /></mxCell>'
)

mxfile = (
    f'<mxfile host="app.diagrams.net"><diagram id="grow8-erd-part2" '
    f'name="GROW8 Conceptual ERD Part 2"><mxGraphModel dx="1600" dy="900" grid="1" '
    f'gridSize="10" page="1" pageWidth="{W}" pageHeight="{H}" background="#FFFFFF">'
    f"<root>{''.join(cells)}</root></mxGraphModel></diagram></mxfile>"
)

svg = (
    f'<?xml version="1.0" encoding="UTF-8"?>\n'
    f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{W}px" height="{H}px" '
    f'viewBox="0 0 {W} {H}" content="{escape(mxfile)}">\n' + "\n".join(parts) + "\n</svg>\n"
)
OUT.write_text(svg, encoding="utf-8")
print(f"wrote {OUT.name}: {len(nodes)} shapes, {len(segments)} relationship lines")
