"""Fix contacts type constraint to allow 'other' type."""

from alembic import op

revision = '014_contacts_other_type'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('ck_contacts_type', 'contacts', type_='check')
    op.create_check_constraint(
        'ck_contacts_type', 'contacts',
        "type IN ('customer','supplier','both','other')"
    )


def downgrade():
    op.drop_constraint('ck_contacts_type', 'contacts', type_='check')
    op.create_check_constraint(
        'ck_contacts_type', 'contacts',
        "type IN ('customer','supplier','both')"
    )
