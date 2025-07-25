"""add search tokens v1.1.4

Revision ID: 8144e10fcfec
Revises: 7d8bc673e1b2
Create Date: 2025-07-16 13:27:22.852657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import text 
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad 
import base64

from cor_pass.config.config import settings



Base = declarative_base() 
class PatientMigration(Base): 
    __tablename__ = 'patients'
    id = sa.Column(sa.String(36), primary_key=True)
    encrypted_surname = sa.Column(sa.LargeBinary, nullable=True)
    encrypted_first_name = sa.Column(sa.LargeBinary, nullable=True)
    encrypted_middle_name = sa.Column(sa.LargeBinary, nullable=True)
    search_tokens = sa.Column(sa.Text, nullable=True)


def decrypt_data_sync(encrypted_data: bytes, key: bytes) -> str:
    """
    Синхронная функция дешифрования для использования в Alembic миграции.
    """
    if len(key) not in [16, 24, 32]:
        raise ValueError("Key must be 16, 24, or 32 bytes long.")

    try:
        decoded_data = base64.b64decode(encrypted_data)
        iv = decoded_data[: AES.block_size]
        ciphertext = decoded_data[AES.block_size :]

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted_data.decode("utf-8")
    except (ValueError, KeyError, TypeError) as e: 
        print(f"Warning: Decryption failed for some data: {e}")
        return "" 


import re 
def generate_ngrams_migration(text: str, n: int = 2) -> list[str]:
    if not text: return []
    normalized_text = re.sub(r'[^a-zа-я0-9]', '', text.lower())
    if len(normalized_text) < n: return [normalized_text] if normalized_text else []
    ngrams = []
    for i in range(len(normalized_text) - n + 1):
        ngrams.append(normalized_text[i : i + n])
    return ngrams

def get_patient_search_tokens_migration(
    first_name: Union[str, None],
    last_name: Union[str, None],
    middle_name: Union[str, None] = None
) -> str:
    all_tokens = set()
    if first_name:
        all_tokens.update(generate_ngrams_migration(first_name, n=2))
        all_tokens.update(generate_ngrams_migration(first_name, n=3))
    if last_name:
        all_tokens.update(generate_ngrams_migration(last_name, n=2))
        all_tokens.update(generate_ngrams_migration(last_name, n=3))
    if middle_name:
        all_tokens.update(generate_ngrams_migration(middle_name, n=2))
        all_tokens.update(generate_ngrams_migration(middle_name, n=3)) 
    return " ".join(sorted(list(all_tokens)))


# revision identifiers, used by Alembic.
revision: str = '8144e10fcfec'
down_revision: Union[str, None] = '7d8bc673e1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('patients', sa.Column('search_tokens', sa.Text(), nullable=True, server_default=''))
    
    bind = op.get_bind()
    session = Session(bind=bind)

    decoded_key = base64.b64decode(settings.aes_key)

    for patient_mig in session.query(PatientMigration).yield_per(1000):
        decrypted_surname = None
        decrypted_first_name = None
        decrypted_middle_name = None

        if patient_mig.encrypted_surname:
            decrypted_surname = decrypt_data_sync(patient_mig.encrypted_surname, decoded_key)
        if patient_mig.encrypted_first_name:
            decrypted_first_name = decrypt_data_sync(patient_mig.encrypted_first_name, decoded_key)
        if patient_mig.encrypted_middle_name:
            decrypted_middle_name = decrypt_data_sync(patient_mig.encrypted_middle_name, decoded_key)
        
        patient_mig.search_tokens = get_patient_search_tokens_migration(
            first_name=decrypted_first_name,
            last_name=decrypted_surname,
            middle_name=decrypted_middle_name
        )
        session.add(patient_mig) 
    
    session.commit() 

    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_column('patients', 'search_tokens')

