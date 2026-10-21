# Findly lecturer demonstration

## 1. Start the local application

Follow README.md once to create `.venv` and install requirements. For real sentence embeddings, install the optional lock file and run `python manage.py prepare-model` before the presentation. Internet is not needed during the demonstration once dependencies and weights are installed.

Run `RUN_DEMO.cmd`, wait for “Application startup complete,” and open http://127.0.0.1:8001/. A “Demonstration data” label distinguishes this database from real reports. The ordinary installation starts separately with `START_FINDLY.cmd` on port 8002.

| Purpose | Email | Password |
| --- | --- | --- |
| Owner | student.demo@example.com | FindlyDemo2026! |
| Finder | finder.demo@example.com | FindlyDemo2026! |
| Officer | security.demo@example.com | FindlyDemo2026! |
| Administrator | admin.demo@example.com | FindlyDemo2026! |

These credentials and all seeded reports are synthetic. `seed-demo` only targets `findly-demo.db`; it does not add accounts to your real database. Re-running it is safe and preserves progress. A new installation generates the eight initial sample reports. Additional examples are created through the application.

## 2. Show registration and login

The login screen offers Sign up. A new campus user supplies a name, email, password, campus and student/staff role; officers are provisioned by a trusted operator. Log in as the owner above for the prepared examples. Use Profile → Log out to switch accounts. Do not expose real credentials or private documents during the presentation.

## 3. Report a loss

On Home, point to the two main actions. Choose **I lost something** and enter:

- Item name: Orange scientific calculator (use a fresh distinctive title if this example was already run).
- Category: Electronics; colour: Orange; brand: Casio.
- Description: Orange Casio scientific calculator with a dark protective sleeve, left in the engineering laboratory.
- Location: Engineering laboratory; date: yesterday.
- A photograph is optional.

Submit. If no similar found report exists, Findly saves the report and says it will notify you when something similar is reported. The report stays active. It does not need a perfect score or a manual search.

## 4. Report a find from the second account

Log out and sign in as the finder. Choose **I found something**:

- Item name: Casio study calculator.
- Description: A tangerine Casio scientific calculator in a dark cover, picked up in the engineering lab.
- Same category/colour/brand; location Engineering laboratory; date today.
- Storage: Campus security desk.
- Upload one or more synthetic item photographs (up to four, 3 MB each).

Submit. The backend compares it against existing active losses automatically. Scores are recalculated from the current data; the demonstration never hardcodes a percentage.

## 5. Explain the automatic matching

The sample pink bottle and rose flask illustrate different vocabulary. The black Samsung phone and blue Adidas backpack illustrate a strong contradiction. Silver keys and a laptop sleeve provide other plausible pairs.

Say: “TF-IDF gives distinctive words more weight. Cosine similarity measures how closely text vectors align. Optional MiniLM sentence vectors help with different wording. Category, colour, brand, date, location and item name add evidence; contradictions lower the score.”

The Matches page shows the active matching mode. If it says TF-IDF + contextual synonyms + attributes, the semantic model is unavailable or disabled; do not claim embeddings are running. A score is a suggestion, not a probability that the item belongs to somebody. See ARCHITECTURE.md for the exact weights.

## 6. Demonstrate the notification

Log back in as the owner. The new qualifying match appears in Notifications, with an unread count. Open **View potential match →** to go directly to that pair. The alert is stored in SQLite and survives restart; it is not a temporary popup. Rechecking the same pair does not create duplicate match alerts. Active sessions refresh safely approximately every 15 seconds.

## 7. Submit a private ownership claim

In the match details inspect the photos, reasons, dates and descriptions. Click **This Might Be Mine**. Explain ownership and add a detail such as “small triangle scratched inside the sliding cover.” Link the corresponding lost report so recovery can close it. Optionally attach a synthetic receipt or prior-possession picture.

Submit. The claim is Pending. The finder cannot approve it and cannot read its private evidence. The similarity engine does not decide ownership.

## 8. Verify and recover as an officer

Sign in as the officer. Review Claims is now available. Open the claim, inspect its private description and optional file, and record review notes.

Demonstrate **More Information Required** first. Switch to the owner, open My Claims, supply another private detail, and send it. Return as the officer and approve only after comparing the evidence. Approval reserves the item; it does not record a physical handover.

After the simulated owner collects it, choose **Confirm recovery**, record a handover reason, and confirm. The claim becomes Recovered, the found item becomes Recovered, and only the explicitly linked lost report becomes Recovered. Notifications and audit history record the decisions.

Rejection is also supported and tested by the API suite. Use a separate synthetic claim if demonstrating rejection; a completed claim should remain a historical record.

## 9. Show where information is stored

- Demo database: `findly-demo.db`; real working-copy database: `lost_and_found.db`.
- Domain tables: users, lost_items, found_items, matches, claims, claim_evidence, notifications, status_history.
- Pictures and proof: `data-demo/report_images/` and `data-demo/evidence/`; the database stores opaque references.
- Schema upgrades: `migrations/versions/`; automatic pre-change copies: `backups/`.
- Score breakdown: matches.score_components, including mode, component weights and contradiction penalties.

Use a read-only database viewer if desired. Do not edit live rows to simulate a result: use the UI so permissions, notifications and audit records remain consistent. Administrator → Activity Log shows the history without directly changing the database.

## 10. Finish with the architecture and honest scope

Open ARCHITECTURE.md and explain: vanilla browser frontend → authenticated FastAPI API → SQLAlchemy/SQLite, with a Python matcher and protected file storage. Officers make ownership decisions. All runtime processing is local after setup; images are not analyzed by AI. The optional model is English-focused and may make mistakes. The prototype has automated tests and browser checks, not a production accuracy certification.

For evidence, open TESTING.md. To run the suite live, use `python -m pytest -q`; without the optional downloaded model its one embedding test is explicitly skipped.
