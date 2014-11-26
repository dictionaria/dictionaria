"""fix polymorphic_type

Revision ID: 3659fbd1a6c1
Revises: 
Create Date: 2014-11-26 14:23:38.888000

"""

# revision identifiers, used by Alembic.
revision = '3659fbd1a6c1'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    update_pmtype(['contribution', 'parameter', 'unit', 'value'], 'base', 'custom')


def downgrade():
    update_pmtype(['contribution', 'parameter', 'unit', 'value'], 'custom', 'base')


def update_pmtype(tablenames, before, after):
    for table in tablenames:
        op.execute(sa.text('UPDATE %s SET polymorphic_type = :after '
            'WHERE polymorphic_type = :before' % table
            ).bindparams(before=before, after=after))
