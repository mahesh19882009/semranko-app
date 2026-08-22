"""Persist the durable multi-target identity for tracked keywords.

The migration deliberately aborts, without committing, when an existing row
cannot be resolved from trusted project/canonical-catalog data or when the new
identity would collide. It never merges or deletes Keyword rows.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import op
import sqlalchemy as sa

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "fastapi_app"))
from app.services.keyword_identity import catalog_location_labels, resolve_legacy_keyword_target

revision = "phase21_keyword_target_identity"
down_revision = "phase20_entitlement_snapshots"
branch_labels = None
depends_on = None

def _indexes(connection) -> set[str]:
    return {index["name"] for index in sa.inspect(connection).get_indexes("Keyword")}


def upgrade() -> None:
    connection = op.get_bind()
    op.add_column("Keyword", sa.Column("locationCode", sa.Integer(), nullable=True))

    projects = {
        row["id"]: dict(row)
        for row in connection.execute(sa.text('SELECT "id", "location", "locationCode" FROM "Project"')).mappings()
    }
    labels = catalog_location_labels()
    rows = [dict(row) for row in connection.execute(sa.text('SELECT "id", "projectId", "keyword", "location", "device" FROM "Keyword"')).mappings()]

    updates: list[tuple[str, str, int, str]] = []
    unresolved: list[str] = []
    seen: dict[tuple[str, str, int, str], str] = {}
    for row in rows:
        project = projects.get(row["projectId"], {})
        resolved = resolve_legacy_keyword_target(row, project, labels)
        if resolved[0] is None:
            unresolved.append(f"{row['id']}: {resolved[1]}")
            continue
        keyword, code, device = resolved
        identity = (row["projectId"], keyword, code, device)
        if identity in seen:
            raise RuntimeError(
                "Phase 2 migration refused: target identity collision between "
                f"Keyword rows {seen[identity]} and {row['id']} for {identity}. "
                "No rows were merged or deleted."
            )
        seen[identity] = row["id"]
        updates.append((row["id"], keyword, code, device))

    if unresolved:
        preview = "; ".join(unresolved[:20])
        suffix = " ..." if len(unresolved) > 20 else ""
        raise RuntimeError(
            "Phase 2 migration refused: unresolved Keyword locations/devices "
            f"({len(unresolved)}): {preview}{suffix}. "
            "Resolve these rows explicitly and rerun; no rows were merged or deleted."
        )

    for row_id, keyword, code, device in updates:
        connection.execute(sa.text('''
            UPDATE "Keyword"
            SET "keyword" = :keyword, "locationCode" = :location_code, "device" = :device
            WHERE "id" = :row_id
        '''), {"row_id": row_id, "keyword": keyword, "location_code": code, "device": device})

    if "Keyword_projectId_keyword_key" in _indexes(connection):
        op.drop_index("Keyword_projectId_keyword_key", table_name="Keyword")

    with op.batch_alter_table("Keyword") as batch:
        batch.alter_column("locationCode", existing_type=sa.Integer(), nullable=False)

    op.create_index(
        "Keyword_projectId_keyword_locationCode_device_key",
        "Keyword",
        ["projectId", "keyword", "locationCode", "device"],
        unique=True,
    )


def downgrade() -> None:
    connection = op.get_bind()
    duplicate = connection.execute(sa.text('''
        SELECT 1 FROM "Keyword"
        GROUP BY "projectId", "keyword"
        HAVING COUNT(*) > 1
        LIMIT 1
    ''')).first()
    if duplicate:
        raise RuntimeError(
            "Phase 2 downgrade refused: multi-target Keyword rows exist and "
            "the old (projectId, keyword) identity cannot represent them without loss."
        )

    if "Keyword_projectId_keyword_locationCode_device_key" in _indexes(connection):
        op.drop_index("Keyword_projectId_keyword_locationCode_device_key", table_name="Keyword")
    op.create_index("Keyword_projectId_keyword_key", "Keyword", ["projectId", "keyword"], unique=True)
    with op.batch_alter_table("Keyword") as batch:
        batch.drop_column("locationCode")
