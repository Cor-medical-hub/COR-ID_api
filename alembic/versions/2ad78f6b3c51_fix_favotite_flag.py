"""fix favotite flag

Revision ID: 2ad78f6b3c51
Revises: d17edc5eba47
Create Date: 2024-11-05 13:46:11.852502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ad78f6b3c51'
down_revision: Union[str, None] = 'd17edc5eba47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###