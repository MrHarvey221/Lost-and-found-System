from alembic import context
from database import Base, make_engine
from config import Settings
import models  # registers the eight tables


def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get('connection')
if connection is not None:
    run(connection)
else:
    from migration_safety import backup_and_validate
    engine = make_engine(Settings.from_env().prepare().database_url)
    backup_and_validate(engine)
    with engine.begin() as connection:
        run(connection)
    engine.dispose()
