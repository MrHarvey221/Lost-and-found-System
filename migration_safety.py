"""Back up a populated SQLite file before upgrade; never erase conflicting data."""
from datetime import datetime, UTC
from pathlib import Path
import sqlite3
import uuid
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from config import ROOT


def backup_and_validate(engine):
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        current = connection.execute(text('SELECT version_num FROM alembic_version')).scalar() if 'alembic_version' in tables else None
    head = ScriptDirectory.from_config(Config(str(ROOT / 'alembic.ini'))).get_current_head()
    if current == head or not tables:
        return
    source = Path(engine.url.database)
    backup_dir = source.parent / 'backups'
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / f'{source.stem}-{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}.db'
    with sqlite3.connect(source) as src, sqlite3.connect(backup) as dst:
        src.backup(dst)
    print(f'Database backup created: {backup}')
    with engine.connect() as connection:
        from migrations.legacy_models import Base as LegacyBase
        for table in LegacyBase.metadata.sorted_tables:
            if table.name in tables:
                columns = {c['name'] for c in inspect(connection).get_columns(table.name)}
                missing = set(table.columns.keys()) - columns
                if missing:
                    raise RuntimeError(f'Legacy table {table.name} is missing expected columns {sorted(missing)}. No guessed schema repair was attempted. Backup: {backup}')
        if connection.execute(text('PRAGMA foreign_key_check')).first():
            raise RuntimeError(f'Legacy database has broken foreign keys; repair before migration. Backup: {backup}')
        checks = [
            ('users', 'SELECT lower(email) FROM users GROUP BY lower(email) HAVING count(*)>1', 'duplicate email addresses'),
            ('matches', 'SELECT lost_item_id FROM matches GROUP BY lost_item_id,found_item_id HAVING count(*)>1', 'duplicate match pairs'),
            ('claims', "SELECT found_item_id FROM claims WHERE claim_status IN ('approved','claim_approved','completed') GROUP BY found_item_id HAVING count(*)>1", 'multiple approved claims on one item'),
            ('claims', "SELECT claimant_id FROM claims WHERE claim_status IN ('submitted','more_information','approved','claim_approved','completed') GROUP BY claimant_id,found_item_id HAVING count(*)>1", 'duplicate active claims'),
        ]
        for table, sql, problem in checks:
            if table in tables and connection.execute(text(sql)).first():
                raise RuntimeError(f'Legacy database contains {problem}. No records were removed. Resolve explicitly and retry. Backup: {backup}')


def upgrade_database(engine):
    backup_and_validate(engine)
    config = Config(str(ROOT / 'alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
    with engine.connect() as connection:
        if connection.execute(text('PRAGMA foreign_key_check')).first():
            raise RuntimeError('Foreign key validation failed after migration.')
