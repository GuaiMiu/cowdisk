"""add config and audit tables

Revision ID: 20260210_add_config_audit
Revises: 
Create Date: 2026-02-10 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260210_add_config_audit"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "bn_config" not in tables:
        op.create_table(
            "bn_config",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("scope_type", sa.String(length=32), nullable=False),
            sa.Column("scope_id", sa.String(length=64), nullable=True),
            sa.Column("key", sa.String(length=191), nullable=False),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("value_type", sa.String(length=16), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_secret", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("updated_by", sa.Integer(), nullable=True),
        )
        op.create_index("ix_bn_config_key", "bn_config", ["key"])
        op.create_index(
            "ux_bn_config_scope_key",
            "bn_config",
            ["scope_type", "scope_id", "key"],
            unique=True,
        )
    else:
        existing_cols = {col["name"] for col in inspector.get_columns("bn_config")}
        if "scope_type" not in existing_cols:
            op.add_column(
                "bn_config",
                sa.Column(
                    "scope_type",
                    sa.String(length=32),
                    nullable=False,
                    server_default="GLOBAL",
                ),
            )
        if "scope_id" not in existing_cols:
            op.add_column(
                "bn_config",
                sa.Column("scope_id", sa.String(length=64), nullable=True),
            )
        if "value_type" not in existing_cols:
            op.add_column(
                "bn_config",
                sa.Column(
                    "value_type",
                    sa.String(length=16),
                    nullable=False,
                    server_default="string",
                ),
            )
        if "description" not in existing_cols:
            op.add_column(
                "bn_config",
                sa.Column("description", sa.Text(), nullable=True),
            )
        if "is_secret" not in existing_cols:
            op.add_column(
                "bn_config",
                sa.Column(
                    "is_secret",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )
        if "created_at" not in existing_cols:
            op.add_column(
                "bn_config",
                sa.Column("created_at", sa.DateTime(), nullable=True),
            )
        if "updated_at" not in existing_cols:
            op.add_column(
                "bn_config",
                sa.Column("updated_at", sa.DateTime(), nullable=True),
            )
        if "updated_by" not in existing_cols:
            op.add_column(
                "bn_config",
                sa.Column("updated_by", sa.Integer(), nullable=True),
            )
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("bn_config")}
        if "ix_bn_config_key" not in existing_indexes:
            op.create_index("ix_bn_config_key", "bn_config", ["key"])
        if "ux_bn_config_scope_key" not in existing_indexes:
            op.create_index(
                "ux_bn_config_scope_key",
                "bn_config",
                ["scope_type", "scope_id", "key"],
                unique=True,
            )

    if "bn_audit_log" not in tables:
        op.create_table(
            "bn_audit_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("resource_type", sa.String(length=32), nullable=True),
            sa.Column("resource_id", sa.String(length=64), nullable=True),
            sa.Column("path", sa.Text(), nullable=True),
            sa.Column("ip", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_bn_audit_log_created_at", "bn_audit_log", ["created_at"])
        op.create_index("ix_bn_audit_log_user_id", "bn_audit_log", ["user_id"])
        op.create_index("ix_bn_audit_log_action", "bn_audit_log", ["action"])

    if "BN_CONFIG" in tables:
        meta = sa.MetaData()
        old_table = sa.Table("BN_CONFIG", meta, autoload_with=bind)
        new_table = sa.Table("bn_config", meta, autoload_with=bind)
        rows = bind.execute(sa.select(old_table)).fetchall()
        if rows:
            for row in rows:
                bind.execute(
                    new_table.insert().values(
                        scope_type="GLOBAL",
                        scope_id=None,
                        key=row.key,
                        value=row.value or "",
                        value_type="string",
                        description=getattr(row, "description", None),
                        is_secret=False,
                        created_at=getattr(row, "created_at", None),
                        updated_at=getattr(row, "updated_at", None),
                        updated_by=None,
                    )
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "bn_audit_log" in tables:
        op.drop_index("ix_bn_audit_log_action", table_name="bn_audit_log")
        op.drop_index("ix_bn_audit_log_user_id", table_name="bn_audit_log")
        op.drop_index("ix_bn_audit_log_created_at", table_name="bn_audit_log")
        op.drop_table("bn_audit_log")
    if "bn_config" in tables:
        op.drop_index("ux_bn_config_scope_key", table_name="bn_config")
        op.drop_index("ix_bn_config_key", table_name="bn_config")
        op.drop_table("bn_config")
