"""add last password change model

Revision ID: 60e4b41db7bb
Revises: 651ebe0b7b62
Create Date: 2024-10-17 14:54:40.938112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60e4b41db7bb'
down_revision: Union[str, None] = '651ebe0b7b62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Добавление нового столбца без значения по умолчанию
    op.add_column('users', sa.Column('last_password_change', sa.DateTime(), nullable=True))
    
    # Обновление всех существующих записей новым значением
    op.execute("UPDATE users SET last_password_change = datetime('now')")

def downgrade():
    op.drop_column('users', 'last_password_change')
