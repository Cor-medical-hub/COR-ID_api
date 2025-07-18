"""add is printed for sample and case v1.0.14

Revision ID: 37567c675f11
Revises: 7a3f6c78cff1
Create Date: 2025-07-07 14:29:34.297049

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "37567c675f11"
down_revision: Union[str, None] = "7a3f6c78cff1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "cases", sa.Column("is_printed_cassette", sa.Boolean(), nullable=True)
    )
    op.add_column("cases", sa.Column("is_printed_glass", sa.Boolean(), nullable=True))
    op.add_column("cases", sa.Column("is_printed_qr", sa.Boolean(), nullable=True))
    op.add_column(
        "samples", sa.Column("is_printed_cassette", sa.Boolean(), nullable=True)
    )
    op.add_column("samples", sa.Column("is_printed_glass", sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("samples", "is_printed_glass")
    op.drop_column("samples", "is_printed_cassette")
    op.drop_column("cases", "is_printed_qr")
    op.drop_column("cases", "is_printed_glass")
    op.drop_column("cases", "is_printed_cassette")
    # ### end Alembic commands ###
