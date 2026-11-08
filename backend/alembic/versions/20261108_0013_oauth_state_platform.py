"""oauth states carry platform and username for chess.com oauth

Revision ID: 20261108_0013
Revises: 20261107_0012
Create Date: 2026-11-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20261108_0013"
down_revision = "20261107_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("oauth_states", sa.Column("platform", sa.String(length=16), nullable=False, server_default="lichess"))
    op.add_column("oauth_states", sa.Column("username", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("oauth_states", "username")
    op.drop_column("oauth_states", "platform")
