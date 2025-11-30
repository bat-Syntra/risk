"""Add feedbacks and vouches tables

Revision ID: add_feedbacks_vouches
Revises: 
Create Date: 2025-11-29 00:25:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'add_feedbacks_vouches'
down_revision = None  # Update this with your latest revision
branch_labels = None
depends_on = None


def upgrade():
    # Create user_feedbacks table
    op.create_table(
        'user_feedbacks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('bet_id', sa.Integer(), nullable=True),
        sa.Column('feedback_type', sa.String(20), nullable=False),  # 'good' or 'bad'
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('bet_type', sa.String(20), nullable=True),  # 'middle', 'arbitrage', 'good_ev'
        sa.Column('bet_amount', sa.Float(), nullable=True),
        sa.Column('profit', sa.Float(), nullable=True),
        sa.Column('match_info', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('seen_by_admin', sa.Boolean(), default=False),
    )
    
    # Create user_vouches table
    op.create_table(
        'user_vouches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('bet_id', sa.Integer(), nullable=False),
        sa.Column('bet_type', sa.String(20), nullable=False),  # 'middle', 'arbitrage', 'good_ev'
        sa.Column('bet_amount', sa.Float(), nullable=False),
        sa.Column('profit', sa.Float(), nullable=False),
        sa.Column('match_info', sa.Text(), nullable=False),
        sa.Column('match_date', sa.Date(), nullable=True),
        sa.Column('sport', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('seen_by_admin', sa.Boolean(), default=False),
    )
    
    # Add indexes
    op.create_index('idx_feedbacks_user_id', 'user_feedbacks', ['user_id'])
    op.create_index('idx_feedbacks_created_at', 'user_feedbacks', ['created_at'])
    op.create_index('idx_feedbacks_seen', 'user_feedbacks', ['seen_by_admin'])
    
    op.create_index('idx_vouches_user_id', 'user_vouches', ['user_id'])
    op.create_index('idx_vouches_created_at', 'user_vouches', ['created_at'])
    op.create_index('idx_vouches_profit', 'user_vouches', ['profit'])
    op.create_index('idx_vouches_seen', 'user_vouches', ['seen_by_admin'])


def downgrade():
    op.drop_table('user_vouches')
    op.drop_table('user_feedbacks')
