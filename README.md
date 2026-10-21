# Findly — Campus Lost and Found System

**Report → Automatically match → Notify → Verify → Recover.**

Findly helps students and university staff report lost/found belongings, receive explainable matches and claim items through an authorized officer. This repository includes the HTML/CSS/JavaScript frontend, complete Python FastAPI backend, SQLite/SQLAlchemy database models, Alembic migrations, matching engine, tests and synthetic demo-data setup.

## Install on Windows

Python **3.14.7 on Windows** was used for validation. Open **Command Prompt**:

```bat
git clone https://github.com/MrHarvey221/Lost-and-found-System.git
cd Lost-and-found-System
py -3.14 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-lock.txt
```

If the Python launcher is unavailable, verify `python --version` and use `python -m venv .venv` with the correct interpreter. No Node/React build is required.

### Run the lecturer demonstration

```bat
RUN_DEMO.cmd
```

Wait for **Application startup complete**, then open **http://127.0.0.1:8001/**. Keep the terminal open; **Ctrl+C** stops the server. After setup, double-clicking `RUN_DEMO.cmd` starts it again.

The launcher creates an isolated `findly-demo.db` and `data-demo/`. All synthetic accounts use **FindlyDemo2026!**:

| Email | Role |
| --- | --- |
| student.demo@example.com | Owner/student |
| finder.demo@example.com | Finder/student |
| security.demo@example.com | Security officer |
| admin.demo@example.com | Administrator |

Demo setup is opt-in and idempotent. Scores come from the actual Python engine; sample illustrations are labelled. See [DEMO_GUIDE.md](DEMO_GUIDE.md).

### Run an ordinary installation

```bat
python manage.py migrate
START_FINDLY.cmd
```

Open **http://127.0.0.1:8002/**. This uses `lost_and_found.db` and `data/` by default. A clean clone creates a fresh database. Sign up creates student/staff accounts. Provision officers/admins through a trusted local terminal:

```bat
python manage.py create-user --email officer@example.com --name Campus --surname Officer --role security
python manage.py create-user --email admin@example.com --name Campus --surname Admin --role administrator
```

These commands prompt for passwords; ordinary installations have no default administrator password. `python manage.py reset-password --email name@example.com` resets access and revokes old sessions.

### Optional sentence embeddings

The base setup works with scikit-learn TF-IDF/cosine, contextual synonyms and attributes. To enable the tested local semantic model:

```bat
python -m pip install -r requirements-semantic-lock.txt
python manage.py prepare-model
```

Restart the server. Preparation explicitly downloads `sentence-transformers/all-MiniLM-L6-v2` and records its revision. Runtime descriptions stay local; CPU inference uses downloaded files. First model loading can take time. Missing dependencies/weights or failed inference activate the clearly identified fallback mode. `SEMANTIC_MODE=off` forces fallback.

Scores are similarity suggestions, not probabilities of ownership. Photographs support human inspection; image recognition is not implemented.

## Database backend

| File/directory | Purpose |
| --- | --- |
| `database.py` | Engine, SQLite connections, foreign-key enforcement and request transactions |
| `models.py` | User, LostItem, FoundItem, Match, Claim, ClaimEvidence, Notification and StatusHistory |
| `schemas.py` | Validated API contracts |
| `crud.py` | Report, claim, audit, ownership and recovery rules |
| `migrations/`, `alembic.ini` | Database creation/upgrades, revisions 0001–0003 |
| `migration_safety.py` | Preflight checks and backups before upgrading supported databases |
| `data_migration.py` | Supported legacy inline photograph conversion |
| `manage.py`, `demo.py` | Database setup, operator commands and isolated synthetic data |

**Database records are generated locally.** Live `.db` files, real accounts, private evidence, uploaded photos, session secrets and model weights are excluded from Git. The source and migrations create a fully working database after cloning.

Before upgrading an existing installation, back up both its database and upload directory, configure the intended paths and run `python manage.py migrate`. Conflicting legacy records stop migration for review instead of being deleted. Keep the original deployment separate from the copy being upgraded.

## Configuration

Defaults work without `.env`. Copy `.env.example` to `.env` to customize:

| Setting | Default/purpose |
| --- | --- |
| `DATABASE_URL` | `sqlite:///./lost_and_found.db` |
| `DATA_DIR` | `./data` |
| `MATCH_THRESHOLD` | 45 similarity points |
| `SEMANTIC_MODE` | `auto` or `off` |
| `SEMANTIC_MODEL_DIR` | `./models/all-MiniLM-L6-v2` |
| `SESSION_HOURS` | 12 |
| `SESSION_SECRET` | Generated privately in the data directory when omitted |
| `COOKIE_SECURE` | `false` for local HTTP; `true` requires HTTPS |
| `DEMO_MODE` | `false`; the demo launcher enables it |

Paths resolve against the project directory. Use the Python server URL; opening `index.html` directly does not run the API. GitHub Pages cannot run the Python/SQLite backend.

## Verification and recovery

FastAPI enforces roles and ownership. Students/staff report and claim; security/lost property officers review private evidence, request more information, approve/reject and confirm physical collection. Administrators also manage account access and global audit history.

Approval reserves the found item. A separate officer handover completes recovery and closes only the claimant's linked lost report. Matching never automatically approves ownership. Storage locations and private evidence have restricted access.

Found reports accept up to four photos; lost reports one optional photo. JPG/PNG/WEBP images are validated and re-encoded with a 3 MB per-file limit. Private proof can also be PDF and is downloaded through authorized endpoints. In-app notifications work without email credentials.

## Tests

```bat
python -m pytest -q --junitxml=test-results/pytest.xml
```

Tests cover authentication, database persistence, delayed/reverse matching, notifications, deduplication, private evidence, roles, concurrent officer decisions, uploads, migration preservation and demo setup. Without the optional model, the real embedding test is explicitly skipped. See [TESTING.md](TESTING.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

This is a local university prototype. The separate academic LaTeX/PDF report is not included in this repository.
