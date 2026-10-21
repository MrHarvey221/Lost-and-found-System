"""SQLAlchemy sessions with SQLite foreign keys on every connection."""
from fastapi import Request
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def make_engine(url):
    engine = create_engine(url, connect_args={'check_same_thread': False, 'timeout': 30})

    @event.listens_for(engine, 'connect')
    def configure_sqlite(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA busy_timeout=30000')

    return engine


def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db(request: Request):
    with request.app.state.sessions() as db:
        try:
            # Reserve the SQLite writer before checking mutable state. Concurrent
            # officer decisions must read the preceding committed decision, rather
            # than overwrite it after reading an earlier claim/item status.
            if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
                db.execute(text('BEGIN IMMEDIATE'))
            yield db
        except Exception:
            db.rollback()
            raise
