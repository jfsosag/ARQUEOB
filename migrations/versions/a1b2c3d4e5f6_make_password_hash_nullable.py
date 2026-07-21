"""make password_hash nullable for optional passwords

Revision ID: a1b2c3d4e5f6
Revises: 2919e6c334fe
Create Date: 2026-07-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '2919e6c334fe'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.alter_column('password_hash', nullable=True)


def downgrade():
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.alter_column('password_hash', nullable=False)
