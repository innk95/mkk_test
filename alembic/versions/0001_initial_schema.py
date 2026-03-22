"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-21

"""
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SQL_DIR = Path(__file__).parent.parent / "sql"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS ltree")

    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("path", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["activities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("ALTER TABLE activities ALTER COLUMN path TYPE ltree USING path::ltree")
    op.execute("ALTER TABLE activities ADD CONSTRAINT chk_activities_depth CHECK (nlevel(path) <= 3)")
    op.create_index("ix_activities_parent_id", "activities", ["parent_id"])
    op.execute("CREATE INDEX ix_activities_path ON activities USING gist(path)")

    op.execute((_SQL_DIR / "update_activity_path.sql").read_text())

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("building_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_building_id", "organizations", ["building_id"])

    op.create_table(
        "organization_phones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organization_phones_organization_id", "organization_phones", ["organization_id"])

    op.create_table(
        "organization_activity",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id", "activity_id"),
    )


def downgrade() -> None:
    op.drop_table("organization_activity")
    op.drop_index("ix_organization_phones_organization_id", table_name="organization_phones")
    op.drop_table("organization_phones")
    op.drop_index("ix_organizations_building_id", table_name="organizations")
    op.drop_table("organizations")
    op.execute("DROP TRIGGER IF EXISTS trg_cascade_update_activity_path ON activities")
    op.execute("DROP FUNCTION IF EXISTS cascade_update_activity_path()")
    op.execute("DROP TRIGGER IF EXISTS trg_update_activity_path ON activities")
    op.execute("DROP FUNCTION IF EXISTS update_activity_path()")
    op.execute("DROP INDEX IF EXISTS ix_activities_path")
    op.execute("DROP INDEX IF EXISTS ix_activities_parent_id")
    op.drop_table("activities")
    op.drop_table("buildings")
