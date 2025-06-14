"""add_username_and_other_profile_fields_to_user

Revision ID: 0002
Revises: 0001
Create Date: 2025-06-14 06:32:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('username', sa.String(length=80), nullable=False, server_default='temp_username'))
    op.add_column('users', sa.Column('industry_preference', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('contact_phone', sa.String(length=30), nullable=True))
    op.add_column('users', sa.Column('profile_updated_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('users') as batch_op:
        batch_op.create_unique_constraint('uq_users_username', ['username'])
        batch_op.alter_column('username', server_default=None)

def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_username', type_='unique')

    op.drop_column('users', 'profile_updated_at')
    op.drop_column('users', 'contact_phone')
    op.drop_column('users', 'industry_preference')
    op.drop_column('users', 'username')
