"""fix user  models  v1.0.0.21

Revision ID: c6f342d88e9b
Revises: 03adb0968361
Create Date: 2025-05-05 12:55:39.519743

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c6f342d88e9b"
down_revision: Union[str, None] = "03adb0968361"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "device_access_accessing_user_id_key", "device_access", type_="unique"
    )
    op.drop_constraint(
        "device_access_granting_user_id_key", "device_access", type_="unique"
    )
    op.drop_constraint("devices_user_id_key", "devices", type_="unique")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint("devices_user_id_key", "devices", ["user_id"])
    op.create_unique_constraint(
        "device_access_granting_user_id_key", "device_access", ["granting_user_id"]
    )
    op.create_unique_constraint(
        "device_access_accessing_user_id_key", "device_access", ["accessing_user_id"]
    )
    # ### end Alembic commands ###
