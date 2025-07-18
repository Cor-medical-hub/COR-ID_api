"""add add new case status v1.0.10

Revision ID: 9431ea1024c7
Revises: 987ff91460bb
Create Date: 2025-06-30 11:24:54.645460

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9431ea1024c7"
down_revision: Union[str, None] = "987ff91460bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("ALTER TYPE grossing_status ADD VALUE 'CREATED'")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute(
        "ALTER TYPE grossing_status DROP VALUE 'CREATED'"
    )  # PostgreSQL не поддерживает DROP VALUE
    # ### end Alembic commands ###
