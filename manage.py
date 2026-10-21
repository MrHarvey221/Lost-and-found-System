"""Local operator commands. No Git or default demonstration passwords required."""
import argparse
from getpass import getpass
import os
from sqlalchemy import func, select
from config import Settings
from database import make_engine, session_factory
from migration_safety import upgrade_database
from security import hash_password
import crud
import models


def main():
    parser = argparse.ArgumentParser(description='Findly local administration')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('migrate', help='Back up and upgrade the configured database')
    commands.add_parser('prepare-model', help='Download and verify the optional local MiniLM sentence model')
    commands.add_parser('seed-demo', help='Create synthetic accounts/reports in the separate findly-demo.db only')
    create = commands.add_parser('create-user', help='Create an authorized campus account locally')
    create.add_argument('--email', required=True)
    create.add_argument('--name', required=True)
    create.add_argument('--surname', default='')
    create.add_argument('--role', choices=['student','staff','security','lost_property','administrator'], required=True)
    create.add_argument('--password-env', help='Optional environment variable for automation; otherwise prompts securely')
    reset = commands.add_parser('reset-password', help='Set a password for a preserved legacy account or reset access')
    reset.add_argument('--email', required=True)
    reset.add_argument('--password-env')
    args = parser.parse_args()
    if args.command=='seed-demo':
        from demo import demo_settings
        settings=demo_settings().prepare()
    else:
        settings = Settings.from_env().prepare()
    if args.command=='prepare-model':
        from semantic import prepare_model
        print(prepare_model(settings.semantic_model_dir))
        return
    engine = make_engine(settings.database_url)
    try:
        upgrade_database(engine)
        if args.command=='seed-demo':
            from demo import seed_demo
            from matching import MatchEngine
            with session_factory(engine)() as db:
                print(seed_demo(db,MatchEngine(settings.semantic_mode,settings.semantic_model_dir)))
            print('Synthetic data only. All demo passwords: FindlyDemo2026!')
            return
        if args.command == 'migrate':
            print('Database migrations are up to date.')
            return
        password = os.getenv(args.password_env, '') if args.password_env else getpass('Password (at least 10 characters): ')
        if not args.password_env and password != getpass('Confirm password: '):
            parser.error('Passwords do not match.')
        if not 10 <= len(password) <= 128:
            parser.error('Use a password with 10–128 characters.')
        from pydantic import TypeAdapter, EmailStr
        email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
        with session_factory(engine)() as db:
            user = db.scalar(select(models.User).where(func.lower(models.User.email) == email))
            if args.command == 'create-user':
                if user:
                    parser.error('That account exists. Use reset-password to set its password.')
                user = models.User(name=args.name.strip(), surname=args.surname.strip(), email=email,
                                   role=args.role, campus='Main Campus', account_status='active')
                if not user.name:
                    parser.error('Name cannot be empty.')
                db.add(user)
                db.flush()
                crud.history(db, 'user', user.user_id, None, 'active', user.user_id,
                             'Account provisioned by trusted local operator')
            else:
                if not user:
                    parser.error('Account not found.')
                user.auth_version += 1
                crud.history(db, 'user', user.user_id, user.account_status, user.account_status, user.user_id,
                             'Password reset by trusted local operator; sessions revoked')
            user.password_hash = hash_password(password)
            db.commit()
            print(f'Account ready: {user.email} ({user.role}). Password was not printed or stored in plaintext.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
