# System-Design
# URL Shortener — v1

A minimal URL shortener built to learn core system design concepts:
hashing/encoding, database schema design, and API design. No caching
or scaling yet — that's the planned v2/v3.

## How to run (Windows)

```powershell
cd url_shortener
pip install -r requirements.txt
uvicorn main:app --reload
```

This starts the server on your own machine only — it's not a public
website (see `EXPLANATION.md` for what that distinction actually means).
Once it's running, FastAPI auto-generates an interactive testing page
at the `/docs` route on whatever address the terminal shows — open that
in your browser to try the endpoints without needing curl or Postman.

## Endpoints

| Method | Path                       | What it does                                   |
|--------|----------------------------|--------------------------------------------------|
| POST   | `/v1/url`                  | Takes `{"long_url": "...", "custom_url": "..."}` (custom_url optional), returns a short code |
| GET    | `/v1/url/{shorturl}`       | Redirects to the original URL                  |
| GET    | `/v1/url/{shorturl}/stats` | Returns click count + metadata                 |

**Why `/v1/` in the path?** This is API versioning. Once real clients
depend on `/v1/url` behaving a certain way, we can't silently change it
without breaking them. If the API needs to change shape later, `/v2/url`
can run alongside `/v1/url` — old clients keep working, new clients move
to v2 on their own schedule. Baking this in from day one costs nothing
now and avoids a painful migration later.

## How it works

1. **Storage**: SQLite table `urls(id, long_url, short_code, created_at, click_count)`.
   `id` is auto-increment — that's the foundation for the encoding scheme.
2. **Encoding**: The auto-increment `id` gets converted to base62
   (0-9, a-z, A-Z = 62 characters). This is deterministic and collision-free
   by construction, since IDs are already unique. See `encoder.py`.
3. **Custom short codes**: If the request includes `custom_url`, that
   exact string is used as the short code instead of an auto-generated
   one — but only after checking it isn't already taken (returns `409
   Conflict` if it is). This is the one case where collisions genuinely
   can happen, since the user is picking the code instead of the DB.
4. **Dedup (auto-generated codes only)**: If the same long URL is
   shortened twice *without* a custom code, it returns the existing code
   instead of creating a duplicate row. This dedup rule doesn't apply to
   custom codes — a user might reasonably want two different custom
   aliases pointing at the same long URL.
5. **Click tracking**: Every redirect increments `click_count` — the
   groundwork for an analytics feature later.

## Known limitations (intentional, for now)

- **Single point of failure**: one server, one SQLite file. No replication.
- **No caching**: every redirect hits the DB directly. Fine at low traffic,
  will not hold up at scale — SQLite in particular struggles with concurrent writes.
- **Predictable auto-generated codes**: base62-of-an-auto-increment-ID means
  codes are sequential/guessable (`1`, `2`, `3`...) for the non-custom case.
  A production system would likely use a random or hashed code instead,
  trading simplicity for unpredictability.
- **No rate limiting**: anyone can spam `/v1/url` right now.
- **No custom_url validation**: currently accepts any string as a custom
  code (no length limit, no character restrictions, no profanity/reserved-word
  filtering). A real product would validate this input.

## Planned iterations (this is the "system design" part)

- [ ] **v2 — Caching**: add Redis in front of the DB for the redirect
      hot path (most-read, least-written data — classic cache use case).
- [ ] **v3 — Rate limiting**: prevent abuse of `/v1/url`.
- [ ] **v4 — Horizontal scaling**: run multiple app instances behind a
      load balancer; discuss what breaks (SQLite won't work — need
      Postgres/MySQL with a real server).
- [ ] **v5 — Load testing**: use `locust` to find the actual breaking
      point of v1 vs v2, and document the improvement caching gives.

## Design doc

See `DESIGN.md` for requirements, capacity estimates, and architecture
reasoning — this is the artifact that matters most for interviews, more
than the code itself.

## What is this, actually?

See `EXPLANATION.md` for a plain-language walkthrough of what `main.py`
does line by line, and — importantly — what this project *is not* yet
(a live public website), and what would need to be added to make it one.
