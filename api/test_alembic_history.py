"""Regression tests for the repaired Alembic revision graph and PostgreSQL DDL."""

import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.db.models import CreditLedger, FeatureUsage, FeatureUsageReservation, User


def _script_directory():
    config = Config(str(Path(__file__).parent / "alembic.ini"))
    return ScriptDirectory.from_config(config)


def test_migration_graph_has_one_head_and_unique_revisions():
    script = _script_directory()
    revisions = list(script.walk_revisions(base="base", head="heads"))
    revision_ids = [revision.revision for revision in revisions]

    assert len(revision_ids) == len(set(revision_ids))
    assert script.get_heads() == ["phase22_job_keyword_id"]
    assert script.get_revision("phase10_queue_refresh").down_revision == (
        "e5f6a7b8c9d0",
        "drop_unused_tables_phase7e",
    )
    assert script.get_revision("phase10_idempotency").down_revision == "phase10_queue_refresh"
    assert script.get_revision("phase10_3_processing_job_recovery").down_revision == "phase10_idempotency"


def test_postgresql_check_constraints_quote_mixed_case_columns():
    dialect = postgresql.dialect()
    for model, column_name in (
        (User, "creditBalance"),
        (CreditLedger, "balanceBefore"),
        (CreditLedger, "balanceAfter"),
        (FeatureUsage, "usedUnits"),
        (FeatureUsage, "reservedUnits"),
        (FeatureUsageReservation, "consumedUnits"),
    ):
        ddl = str(CreateTable(model.__table__).compile(dialect=dialect))
        assert f'"{column_name}" >= 0' in ddl
