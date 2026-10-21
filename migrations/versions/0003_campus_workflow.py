"""Adopt the running integration's accounts/titles; add galleries and match links."""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    for table in ('lost_items','found_items'):
        if 'image_refs' not in {c['name'] for c in sa.inspect(bind).get_columns(table)}:
            op.add_column(table, sa.Column('image_refs',sa.Text()))
    if 'match_id' not in {c['name'] for c in sa.inspect(bind).get_columns('notifications')}:
        # SQLite supports adding a nullable column with a REFERENCES clause.
        bind.execute(sa.text('ALTER TABLE notifications ADD COLUMN match_id INTEGER REFERENCES matches(match_id)'))
    op.create_index('uq_notification_match','notifications',['recipient_id','match_id','event_type'],unique=True)
    if 'lost_item_id' not in {c['name'] for c in sa.inspect(bind).get_columns('claims')}:
        bind.execute(sa.text('ALTER TABLE claims ADD COLUMN lost_item_id INTEGER REFERENCES lost_items(lost_item_id)'))
    if 'account_credentials' in tables:
        # Preserve the old salted hash exactly. Login upgrades it after verification.
        bind.execute(sa.text("UPDATE users SET password_hash = (SELECT 'legacy_pbkdf2_sha256$310000$' || replace(a.password_hash,':','$') FROM account_credentials a WHERE a.user_id=users.user_id), campus = coalesce((SELECT a.campus FROM account_credentials a WHERE a.user_id=users.user_id),'Main Campus') WHERE password_hash IS NULL AND EXISTS (SELECT 1 FROM account_credentials a WHERE a.user_id=users.user_id)"))
    if 'item_details' in tables:
        for table,prefix,pk in [('lost_items','L-','lost_item_id'),('found_items','F-','found_item_id')]:
            bind.execute(sa.text(f"UPDATE {table} SET title = coalesce((SELECT d.title FROM item_details d WHERE d.item_key=:prefix || {table}.{pk}),title), created_at = coalesce((SELECT d.created FROM item_details d WHERE d.item_key=:prefix || {table}.{pk}),created_at)"),{'prefix':prefix})
    bind.execute(sa.text("UPDATE notifications SET read_at=timestamp WHERE sent_status='read' AND read_at IS NULL"))
    bind.execute(sa.text("UPDATE notifications SET delivery_channel='in_app' WHERE delivery_channel='in-app'"))
    # The earlier integration treated approval as a completed physical return.
    bind.execute(sa.text("UPDATE claims SET claim_status='completed' WHERE claim_status='approved' AND found_item_id IN (SELECT found_item_id FROM found_items WHERE status='returned')"))


def downgrade():
    raise RuntimeError('Restore a backup instead of removing preserved records or fields.')
