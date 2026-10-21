from datetime import date
from pathlib import Path
import pytest
from sqlalchemy import create_engine, inspect, select, text
from database import make_engine, session_factory
from migration_safety import upgrade_database
from migrations import legacy_models as legacy
import models


def test_original_schema_is_migrated_without_losing_data(tmp_path):
    path = tmp_path / 'legacy.db'
    url = 'sqlite:///' + str(path)
    old = create_engine(url)
    legacy.Base.metadata.create_all(old)
    with session_factory(old)() as db:
        person = legacy.User(name='Original',surname='Student',email='legacy@example.com',role='student')
        db.add(person)
        db.flush()
        db.add(legacy.LostItem(reporter_id=person.user_id,category='Books',description='Original textbook',location_lost='Library',date_lost=date(2026,1,1)))
        db.commit()
    old.dispose()
    engine = make_engine(url)
    upgrade_database(engine)
    upgrade_database(engine)  # idempotent; no duplicate backups or destructive reset
    with session_factory(engine)() as db:
        person = db.scalar(select(models.User))
        assert person.email == 'legacy@example.com' and person.password_hash is None
        assert db.scalar(select(models.LostItem)).description == 'Original textbook'
        assert db.execute(text('PRAGMA foreign_keys')).scalar() == 1
        assert db.execute(text('SELECT version_num FROM alembic_version')).scalar() == '0003'
        assert len(inspect(engine).get_table_names()) == 9  # eight domain tables + Alembic bookkeeping
    assert len(list((tmp_path / 'backups').glob('*.db'))) == 1
    engine.dispose()


def test_duplicate_legacy_matches_stop_migration_with_backup(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'dirty.db')
    old = create_engine(url)
    legacy.Base.metadata.create_all(old)
    with session_factory(old)() as db:
        user = legacy.User(name='Original',surname='User',email='dirty@example.com',role='student')
        db.add(user)
        db.flush()
        lost = legacy.LostItem(reporter_id=user.user_id,category='Other',description='Original item',location_lost='Library',date_lost=date(2026,1,1))
        found = legacy.FoundItem(reporter_id=user.user_id,category='Other',description='Original item',location_found='Library',date_found=date(2026,1,1))
        db.add_all([lost,found])
        db.flush()
        db.add_all([legacy.Match(lost_item_id=lost.lost_item_id,found_item_id=found.found_item_id,similarity_score=75) for _ in range(2)])
        db.commit()
    old.dispose()
    engine = make_engine(url)
    with pytest.raises(RuntimeError,match='duplicate match pairs'):
        upgrade_database(engine)
    with engine.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM matches')).scalar() == 2
        assert 'password_hash' not in {column['name'] for column in inspect(connection).get_columns('users')}
    assert list((tmp_path / 'backups').glob('*.db'))
    engine.dispose()
