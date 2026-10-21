"""Baseline: the eight original teammate tables, adopting existing tables in place."""
from alembic import op
from migrations.legacy_models import Base

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError('Destructive downgrades are disabled. Restore a SQLite backup instead.')
