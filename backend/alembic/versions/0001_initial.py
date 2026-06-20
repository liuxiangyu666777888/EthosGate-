"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-20
"""

from alembic import op


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The development app creates SQLAlchemy metadata on startup. This placeholder
    # keeps Alembic wired for production migrations without duplicating schema here.
    pass


def downgrade() -> None:
    pass
