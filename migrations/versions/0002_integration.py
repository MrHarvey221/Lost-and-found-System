"""Add authentication, UI metadata, read receipts, audit indexes and uniqueness."""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    additions = {
        'users': [sa.Column('password_hash', sa.String()),
                  sa.Column('auth_version', sa.Integer(), nullable=False, server_default='0'),
                  sa.Column('campus', sa.String(), nullable=False, server_default='Main Campus')],
        'lost_items': [sa.Column('title', sa.String(), nullable=False, server_default='Lost item'),
                       sa.Column('created_at', sa.DateTime())],
        'found_items': [sa.Column('title', sa.String(), nullable=False, server_default='Found item'),
                        sa.Column('created_at', sa.DateTime())],
        'claims': [sa.Column('review_notes', sa.Text()), sa.Column('created_at', sa.DateTime())],
        'claim_evidence': [sa.Column('created_at', sa.DateTime())],
        'notifications': [sa.Column('read_at', sa.DateTime())],
    }
    for table, columns in additions.items():
        existing = {c['name'] for c in sa.inspect(bind).get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)
    for table in ('lost_items', 'found_items', 'claims', 'claim_evidence'):
        bind.execute(sa.text(f'UPDATE {table} SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL'))
    bind.execute(sa.text("UPDATE claims SET claim_status = substr(claim_status,7) WHERE claim_status IN ('claim_approved','claim_rejected')"))
    indexes = [
        ('uq_users_email_ci', 'users', [sa.text('lower(email)')], True, None),
        ('uq_match_pair', 'matches', ['lost_item_id', 'found_item_id'], True, None),
        ('ix_match_found', 'matches', ['found_item_id'], False, None),
        ('ix_lost_reporter_status', 'lost_items', ['reporter_id', 'status'], False, None),
        ('ix_lost_category_status', 'lost_items', ['category', 'status'], False, None),
        ('ix_found_reporter_status', 'found_items', ['reporter_id', 'status'], False, None),
        ('ix_found_category_status', 'found_items', ['category', 'status'], False, None),
        ('ix_claim_status', 'claims', ['claim_status'], False, None),
        ('ix_claim_reviewer', 'claims', ['reviewer_id'], False, None),
        ('uq_claim_active_owner', 'claims', ['claimant_id', 'found_item_id'], True,
         "claim_status IN ('submitted','more_information','approved','completed')"),
        ('uq_claim_approved_item', 'claims', ['found_item_id'], True,
         "claim_status IN ('approved','completed')"),
        ('ix_evidence_claim', 'claim_evidence', ['claim_id'], False, None),
        ('ix_notification_recipient_time', 'notifications', ['recipient_id','timestamp'], False, None),
        ('ix_history_record', 'status_history', ['related_record_type','related_record_id'], False, None),
        ('ix_history_actor', 'status_history', ['actor_id'], False, None),
    ]
    for name, table, columns, unique, where in indexes:
        # sqlite_master also sees expression indexes that SQLAlchemy cannot reflect.
        exists = bind.execute(sa.text('SELECT 1 FROM sqlite_master WHERE type=:type AND name=:name'),
                              {'type':'index', 'name':name}).first()
        if not exists:
            options = {'sqlite_where': sa.text(where)} if where else {}
            op.create_index(name, table, columns, unique=unique, **options)


def downgrade():
    raise RuntimeError('Destructive downgrades are disabled. Restore a SQLite backup instead.')
