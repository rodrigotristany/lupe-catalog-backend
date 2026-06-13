"""Spec 003 sales

Revision ID: a1b2c3d4e5f6
Revises: eea63c82ae80
Create Date: 2026-06-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "eea63c82ae80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("payment_method", sa.String(length=100), nullable=False),
        sa.Column("total", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sales_created_at", "sales", ["created_at"])
    op.create_index("idx_sales_payment_method", "sales", ["payment_method"])

    op.create_table(
        "sales_products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_name_es", sa.String(length=255), nullable=False),
        sa.Column("product_name_en", sa.String(length=255), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("category_name_es", sa.String(length=100), nullable=True),
        sa.Column("category_name_en", sa.String(length=100), nullable=True),
        sa.Column("price", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sales_products_sale_id", "sales_products", ["sale_id"])
    op.create_index("idx_sales_products_product_id", "sales_products", ["product_id"])
    op.create_index("idx_sales_products_category_id", "sales_products", ["category_id"])

    op.add_column(
        "store_settings",
        sa.Column(
            "payment_methods",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("store_settings", "payment_methods")
    op.drop_index("idx_sales_products_category_id", table_name="sales_products")
    op.drop_index("idx_sales_products_product_id", table_name="sales_products")
    op.drop_index("idx_sales_products_sale_id", table_name="sales_products")
    op.drop_table("sales_products")
    op.drop_index("idx_sales_payment_method", table_name="sales")
    op.drop_index("idx_sales_created_at", table_name="sales")
    op.drop_table("sales")
