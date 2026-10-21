# Verification

Run from the project root using the virtual environment:

```bat
python -m pytest -q --junitxml=test-results/pytest.xml
```

The suite exercises real FastAPI routes with temporary SQLite databases and file storage. It covers authentication, persistence, TF-IDF/attribute matching, optional real embeddings, automatic delayed/reverse notifications, deduplication, protected evidence, role enforcement, competing decisions, recovery, migration backups and demo seeding.

The existing application baseline passed 33 tests with the optional model installed on Windows/Python 3.14.7. A clean source-only clone skips the real embedding test until its model is downloaded: the expected result is 32 passed and one explicit skip. Tests do not require real accounts or property data.

The repository upload copy was independently checked on 21 October 2026: **32 passed, 1 skipped in 91.25 seconds**. The skip was the optional pretrained-model test, because weights are deliberately excluded from source control.

The browser flow was checked with synthetic accounts: loss, later find with two photos, direct notification, private claim, request/respond to more information, approval and separate recovery. Phone-width layouts were checked at 390 and 320 pixels.

These are functional checks, not a campus accuracy benchmark, load test or production security audit. Image recognition and email/SMS are not implemented. The English-focused pretrained model can produce incorrect suggestions.
