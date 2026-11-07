"""oauth states support login purpose (sign in with lichess)

Revision ID: 20261107_0012
Revises: 20261107_0011
Create Date: 2026-11-07
"""

from alembic import op
import sqlalchemy as sa


revision = "20261107_0012"
down_revision = "20261107_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("oauth_states", sa.Column("purpose", sa.String(length=16), nullable=False, server_default="bind"))
    op.alter_column("oauth_states", "user_id", existing_type=sa.String(length=36), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM oauth_states WHERE purpose = 'login'")
    op.alter_column("oauth_states", "user_id", existing_type=sa.String(length=36), nullable=False)
    op.drop_column("oauth_states", "purpose")
