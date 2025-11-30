"""
Add stake randomizer columns to users table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_stake_randomizer'
down_revision = None  # Set to previous migration if needed
branch_labels = None
depends_on = None


def upgrade():
    # Add stake randomizer columns
    op.add_column('users', sa.Column('stake_randomizer_enabled', sa.Boolean(), default=False))
    op.add_column('users', sa.Column('stake_randomizer_amounts', sa.String(20), default=''))  # Ex: "1,5,10"
    op.add_column('users', sa.Column('stake_randomizer_mode', sa.String(10), default='random'))  # 'up', 'down', 'random'


def downgrade():
    op.drop_column('users', 'stake_randomizer_mode')
    op.drop_column('users', 'stake_randomizer_amounts')
    op.drop_column('users', 'stake_randomizer_enabled')
