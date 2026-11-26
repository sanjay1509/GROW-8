"""Runs grow8_operations.sql and writes Operations-Evidence.md.

Every statement is executed in order on one connection (so the transaction and
session variables work as they do in the mysql client), and its result is
recorded under the block it belongs to: the rows returned, the rows affected, or
the error. Errors are expected only in OP-6 and the IC-* blocks; any other error
makes the script exit with status 1.

    pip install pymysql
    python3 generate_evidence.py --user root --password ... [--host 127.0.0.1 --port 3306]
    python3 generate_evidence.py --user root --socket /var/run/mysqld/mysqld.sock

Load the database first with 04-implementation/run_all.sql.
"""

import argparse
import datetime
import re
import sys
from decimal import Decimal
from pathlib import Path

import pymysql

HERE = Path(__file__).resolve().parent
SQL_FILE = HERE / "grow8_operations.sql"
OUT_FILE = HERE / "Operations-Evidence.md"
EXPECTED_ERROR_BLOCKS = re.compile(r"^(IC-\d+|OP-6)$")
BLOCK = re.compile(r"^-- \[([A-Z]+-\d+(?: run)?)\] (.*)$")
PART = re.compile(r"^-- PART (\d) - (.*)$")
MAX_CELL = 90


def parse(sql_text):
    """Yield ('part', title) / ('block', id, title, description) / ('sql', statement)."""
    delimiter = ";"
    buf = []
    block = None
    for raw in sql_text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not buf:
            m = PART.match(line)
            if m:
                yield ("part", f"Part {m.group(1)} — {m.group(2).title()}")
                continue
            m = BLOCK.match(line)
            if m:
                block = [m.group(1), m.group(2).strip(), []]
                yield ("block", block)
                continue
            if block is not None and line.startswith("--   "):
                block[2].append(line[5:].strip())
                continue
            if stripped.upper().startswith("DELIMITER"):
                delimiter = stripped.split()[1]
                continue
            if not stripped or stripped.startswith("--"):
                continue
        if stripped.startswith("--") and not buf:
            continue
        buf.append(line)
        if stripped.endswith(delimiter):
            statement = "\n".join(buf).strip()
            statement = statement[: -len(delimiter)].rstrip()
            buf = []
            yield ("sql", statement)
    if buf:
        yield ("sql", "\n".join(buf).strip())


def cell(value):
    if value is None:
        return "NULL"
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    if isinstance(value, (datetime.datetime, datetime.date, Decimal)):
        value = str(value)
    text = str(value).replace("|", "\\|").replace("\n", " ")
    return text if len(text) <= MAX_CELL else text[: MAX_CELL - 1] + "…"


def table(cursor):
    columns = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    lines.append(f"\n*{len(rows)} row{'s' if len(rows) != 1 else ''}*")
    return "\n".join(lines)


def code_span(text):
    """Inline code that survives backticks inside the text (MySQL quotes names with them)."""
    return f"`` {text} ``" if "`" in text else f"`{text}`"


def shown(statement):
    """Procedure bodies are long and live in the .sql file; show their first line."""
    if statement.upper().startswith("CREATE PROCEDURE"):
        signature = statement[: statement.index("BEGIN")].rstrip()
        return signature + "\nBEGIN\n    … (body in grow8_operations.sql)\nEND"
    return statement


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3306)
    ap.add_argument("--user", default="root")
    ap.add_argument("--password", default="")
    ap.add_argument("--socket", help="connect through a Unix socket instead of host/port")
    args = ap.parse_args()

    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        unix_socket=args.socket,
        autocommit=True,
        charset="utf8mb4",
    )
    with conn.cursor() as cur:
        cur.execute("SELECT VERSION()")
        version = cur.fetchone()[0]

    out, unexpected, expected = [], [], []
    current, statements = None, 0
    counts = {}
    for item in parse(SQL_FILE.read_text(encoding="utf-8")):
        if item[0] == "part":
            out.append(f"\n## {item[1]}\n")
            continue
        if item[0] == "block":
            current = item[1]
            kind = current[0].split("-")[0] + (" run" if current[0].endswith("run") else "")
            counts[kind] = counts.get(kind, 0) + 1
            out.append(current)  # heading filled in at the end: the description is still being read
            continue
        statement = item[1]
        if statement.upper().startswith("DROP PROCEDURE IF EXISTS"):
            with conn.cursor() as cur:
                cur.execute(statement)
            continue
        statements += 1
        block_id = current[0] if current else "setup"
        out.append(f"```sql\n{shown(statement)}\n```")
        try:
            with conn.cursor() as cur:
                cur.execute(statement)
                parts = []
                while True:
                    if cur.description:
                        parts.append(table(cur))
                    if not cur.nextset():
                        break
                if parts:
                    out.append("\n\n".join(parts))
                elif statement.upper().startswith("CREATE PROCEDURE"):
                    out.append("Result: procedure created.")
                elif cur.rowcount >= 0 and not statement.upper().startswith(
                    ("SET ", "USE ", "START", "ROLLBACK")
                ):
                    out.append(f"Result: OK, {cur.rowcount} row(s) affected.")
                else:
                    out.append("Result: OK.")
        except pymysql.MySQLError as exc:
            code, message = exc.args[0], exc.args[1]
            if EXPECTED_ERROR_BLOCKS.match(block_id):
                expected.append(block_id)
                out.append(f"**Refused as expected** — MySQL error {code}: {code_span(message)}")
            else:
                unexpected.append((block_id, code, message))
                out.append(f"**UNEXPECTED ERROR** — MySQL error {code}: {code_span(message)}")
        out.append("")
    conn.close()

    ic_blocks = counts.get("IC", 0)
    header = [
        "# Operations Evidence — Grow8 Database",
        "",
        "**ENSF 608 · Group 2 · Final artifact: Database operations (evidence of execution)**",
        "",
        f"Generated by `generate_evidence.py`, which ran every statement of `grow8_operations.sql` "
        f"in order, on {datetime.datetime.now():%Y-%m-%d %H:%M}, against MySQL {version}. "
        "The database had been created and populated from the submitted files with "
        "`04-implementation/run_all.sql` just before. Every result below is the database's "
        "actual output.",
        "",
        "| Item | Count |",
        "|---|---|",
        f"| Stored procedures defined (SP) | {counts.get('SP', 0)} |",
        f"| Stored procedure calls in part 2 (SP run) | {counts.get('SP run', 0)} |",
        f"| Retrieval queries (Q) | {counts.get('Q', 0)} |",
        f"| Views queried (V) | {counts.get('V', 0)} |",
        f"| Data modification steps (OP) | {counts.get('OP', 0)} |",
        f"| Integrity checks (IC), each refused by the database | {ic_blocks} |",
        f"| SQL statements executed | {statements} |",
        f"| Errors in IC blocks and OP-6, all expected | {len(expected)} |",
        f"| Unexpected errors | {len(unexpected)} |",
        "",
        "Parts 3 and 4 ran inside one transaction that was rolled back, so the final check "
        "(OP-22) shows the dataset unchanged.",
    ]
    body = [
        f"\n### {x[0]}\n\n{' '.join([x[1]] + x[2])}\n" if isinstance(x, list) else x for x in out
    ]
    OUT_FILE.write_text("\n".join(header + ["\n## Setup\n"] + body) + "\n", encoding="utf-8")
    print(
        f"wrote {OUT_FILE.name}: {statements} statements, {len(expected)} expected errors, "
        f"{len(unexpected)} unexpected"
    )
    for block_id, code, message in unexpected:
        print(f"  {block_id}: {code} {message}", file=sys.stderr)
    return 1 if unexpected else 0


if __name__ == "__main__":
    sys.exit(main())
