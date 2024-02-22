"""Create phone number for user database

Revision ID: ba4e8749751f
Revises: 
Create Date: 2024-01-16 17:39:57.053150

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ba4e8749751f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone_number', sa.String(20), nullable=True))


def downgrade() -> None:
    pass
