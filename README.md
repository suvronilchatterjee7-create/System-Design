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

Then open http://localhost:8000/docs for the interactive API explorer
(FastAPI generates this automatically — use it to test without curl/Postman).

## Endpoints

| Method | Path            | What it does                          |
|--------|-----------------|----------------------------------------|
| POST   | `/shorten`      | Takes `{"long_url": "..."}`, returns a short code |
| GET    | `/{code}`       | Redirects to the original URL          |
| GET    | `/stats/{code}` | Returns click count + metadata         |

## How it works

1. **Storage**: SQLite table `urls(id, long_url, short_code, created_at, click_count)`.
   `id` is auto-increment — that's the foundation for the encoding scheme.
2. **Encoding**: The auto-increment `id` gets converted to base62
   (0-9, a-z, A-Z = 62 characters). This is deterministic and collision-free
   by construction, since IDs are already unique. See `encoder.py`.
3. **Dedup**: If the same long URL is shortened twice, it returns the
   existing code instead of creating a duplicate row.
4. **Click tracking**: Every redirect increments `click_count` — the
   groundwork for an analytics feature later.

## Known limitations (intentional, for now)

- **Single point of failure**: one server, one SQLite file. No replication.
- **No caching**: every redirect hits the DB directly. Fine at low traffic,
  will not hold up at scale — SQLite in particular struggles with concurrent writes.
- **Predictable codes**: base62-of-an-auto-increment-ID means codes are
  sequential/guessable (`1`, `2`, `3`...). A production system would likely
  use a random or hashed code instead, trading simplicity for unpredictability.
- **No rate limiting**: anyone can spam `/shorten` right now.

## Planned iterations (this is the "system design" part)

- [ ] **v2 — Caching**: add Redis in front of the DB for the redirect
      hot path (most-read, least-written data — classic cache use case).
- [ ] **v3 — Rate limiting**: prevent abuse of `/shorten`.
- [ ] **v4 — Horizontal scaling**: run multiple app instances behind a
      load balancer; discuss what breaks (SQLite won't work — need
      Postgres/MySQL with a real server).
- [ ] **v5 — Load testing**: use `locust` to find the actual breaking
      point of v1 vs v2, and document the improvement caching gives.

## Design doc

See `DESIGN.md` for requirements, capacity estimates, and architecture
reasoning — this is the artifact that matters most for interviews, more
than the code itself.
