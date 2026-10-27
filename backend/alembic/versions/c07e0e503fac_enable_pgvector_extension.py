"""enable pgvector extension

Revision ID: c07e0e503fac
Revises: c2a00c3abca9
Create Date: 2026-10-26 22:24:36.628970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c07e0e503fac'
down_revision: Union[str, Sequence[str], None] = 'c2a00c3abca9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS vector")
