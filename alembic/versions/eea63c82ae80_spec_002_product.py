"""Spec 002 product

Revision ID: eea63c82ae80
Revises: 0001
Create Date: 2026-04-16 21:06:38.242472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eea63c82ae80'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('priority', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('products', sa.Column('cover_image_id', sa.Integer(), nullable=True))
    op.create_index('idx_products_priority', 'products', ['priority'])
    op.create_foreign_key(
        'fk_products_cover_image_id',
        'products', 'product_images',
        ['cover_image_id'], ['id'],
        ondelete='SET NULL',
        use_alter=True,
    )


def downgrade() -> None:
    op.drop_constraint('fk_products_cover_image_id', 'products', type_='foreignkey')
    op.drop_index('idx_products_priority', table_name='products')
    op.drop_column('products', 'cover_image_id')
    op.drop_column('products', 'priority')
