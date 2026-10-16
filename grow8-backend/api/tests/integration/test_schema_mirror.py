"""CLAUDE.md: ORM models must mirror db/init/001_schema.sql exactly.
This compares the models with the schema actually created from that file."""

import pymysql
import pytest
from grow8_common.db import get_engine
from grow8_common.models import Base
from sqlalchemy import inspect
from sqlalchemy.engine import Inspector
from sqlalchemy.types import TypeEngine

# Names MySQL reports for types that SQLAlchemy spells differently.
_ALIASES = {"BOOL": "TINYINT(1)", "NUMERIC": "DECIMAL"}


def _sql_type(type_: TypeEngine) -> str:
    text = type_.compile(dialect=get_engine().dialect)
    for alias, canonical in _ALIASES.items():
        if text.startswith(alias):
            text = canonical + text[len(alias) :]
    return text.replace(", ", ",")


@pytest.fixture(scope="module")
def inspector(test_db: pymysql.Connection) -> Inspector:
    return inspect(get_engine())


def test_same_tables(inspector: Inspector) -> None:
    assert set(inspector.get_table_names()) == set(Base.metadata.tables)


@pytest.mark.parametrize("table", sorted(Base.metadata.tables))
def test_columns_keys_and_constraints_match(inspector: Inspector, table: str) -> None:
    model = Base.metadata.tables[table]
    kinds = {"UniqueConstraint": set(), "CheckConstraint": set()}
    for constraint in model.constraints:
        kinds.get(type(constraint).__name__, set()).add(constraint.name)

    db_columns = {c["name"]: c for c in inspector.get_columns(table)}
    assert list(db_columns) == [c.name for c in model.columns], "column names/order"
    for column in model.columns:
        db_column = db_columns[column.name]
        assert db_column["nullable"] == column.nullable, f"{column.name} nullability"
        assert _sql_type(db_column["type"]) == _sql_type(column.type), f"{column.name} type"

    assert inspector.get_pk_constraint(table)["constrained_columns"] == [
        c.name for c in model.primary_key
    ]
    fk_names = {fk.name for fk in model.foreign_key_constraints}
    assert {fk["name"] for fk in inspector.get_foreign_keys(table)} == fk_names
    assert {u["name"] for u in inspector.get_unique_constraints(table)} == kinds["UniqueConstraint"]
    # MySQL auto-creates an index per FK when none fits; those carry the FK's name
    db_indexes = {i["name"] for i in inspector.get_indexes(table) if not i["unique"]} - fk_names
    assert db_indexes == {i.name for i in model.indexes}
    assert {c["name"] for c in inspector.get_check_constraints(table)} == kinds["CheckConstraint"]
