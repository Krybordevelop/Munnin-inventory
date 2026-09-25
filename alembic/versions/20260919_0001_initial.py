"""Initial inventory schema.

Revision ID: 20260919_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260919_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_users_username", "admin_users", ["username"], unique=True)
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_name", "projects", ["name"], unique=True)
    op.create_table(
        "project_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_project_token_name"),
    )
    op.create_index("ix_project_tokens_prefix", "project_tokens", ["prefix"], unique=True)
    op.create_index("ix_project_tokens_project_id", "project_tokens", ["project_id"])
    op.create_index("ix_project_tokens_revoked_at", "project_tokens", ["revoked_at"])
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("os_name", sa.String(120), nullable=False),
        sa.Column("os_version", sa.String(120), nullable=False),
        sa.Column("kernel", sa.String(255)),
        sa.Column("cpu_model", sa.String(255)),
        sa.Column("cpu_cores", sa.Integer(), nullable=False),
        sa.Column("ram_bytes", sa.Integer(), nullable=False),
        sa.Column("disk_bytes", sa.Integer(), nullable=False),
        sa.Column("ip_addresses", sa.JSON(), nullable=False),
        sa.Column("inventory", sa.JSON(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("cpu_cores > 0", name="ck_agent_cpu_cores_positive"),
        sa.CheckConstraint("ram_bytes >= 0", name="ck_agent_ram_nonnegative"),
        sa.CheckConstraint("disk_bytes >= 0", name="ck_agent_disk_nonnegative"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "agent_id", name="uq_agent_project_external_id"),
    )
    for column in ("project_id", "status", "hostname", "os_name", "last_seen_at"):
        op.create_index(f"ix_agents_{column}", "agents", [column])
    op.create_index(
        "ix_agents_project_status_seen", "agents", ["project_id", "status", "last_seen_at"]
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_tag_project_name"),
    )
    op.create_index("ix_tags_project_id", "tags", ["project_id"])
    op.create_table(
        "agent_tags",
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("agent_id", "tag_id"),
    )


def downgrade() -> None:
    for table in ("agent_tags", "tags", "agents", "project_tokens", "projects", "admin_users"):
        op.drop_table(table)
