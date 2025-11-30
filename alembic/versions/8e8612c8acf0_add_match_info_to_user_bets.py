"""add_match_info_to_user_bets

Revision ID: 8e8612c8acf0
Revises: 
Create Date: 2025-11-27 20:36:29.249883

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e8612c8acf0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add match info columns to user_bets table
    op.add_column('user_bets', sa.Column('match_name', sa.String(length=255), nullable=True))
    op.add_column('user_bets', sa.Column('sport', sa.String(length=100), nullable=True))
    op.add_column('user_bets', sa.Column('match_date', sa.Date(), nullable=True))


def downgrade() -> None:
    # Remove match info columns from user_bets table
    op.drop_column('user_bets', 'match_date')
    op.drop_column('user_bets', 'sport')
    op.drop_column('user_bets', 'match_name')
