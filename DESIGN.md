# Design Doc: URL Shortener

## 1. Requirements

**Functional**
- Given a long URL, generate a unique short code.
- Given a short code, redirect the user to the original long URL.
- Track how many times a short URL has been visited.

**Non-functional (what we're optimizing for)**
- Low latency on redirect (this is the hot path — every click depends on it).
- Short codes should be as short as possible while staying unique.
- System should be simple to reason about for v1; scaling is a deliberate
  *next* iteration, not solved upfront (over-engineering v1 is a common
  beginner mistake in system design interviews).

## 2. Capacity estimation (back-of-envelope)

This is the part interviewers actually want to see you reason through out loud.

Assume:
- 100 million new URLs shortened per month
- Read:write ratio of 100:1 (redirects far outnumber new shortens — typical
  for this kind of system, since one shortened link gets clicked many times)

**Writes (shorten requests):**
- 100M / month ≈ 100,000,000 / (30 × 24 × 3600) ≈ ~39 writes/sec average

**Reads (redirects):**
- 100:1 ratio → ~3,900 reads/sec average

**Storage:**
- Each row: long_url (~500 bytes avg) + short_code (~7 bytes) + metadata (~50 bytes) ≈ ~600 bytes/row
- 100M new rows/month × 600 bytes ≈ 60 GB/month
- Over 5 years: ~3.6 TB — this tells us we'll eventually need to think about
  storage partitioning, though not on day one.

**Takeaway:** Read traffic dominates by 100x. This is *why* caching is the
first scaling lever to pull (v2), not database replication or sharding —
you cache what gets read the most.

## 3. Why base62 encoding (and the trade-off)

Alternative approaches considered:
- **Random string + collision check**: generate a random 7-char string,
  check DB for collision, retry if taken. Simpler to explain, but wastes
  a DB round-trip on every collision, and collisions become more likely
  as the table grows (birthday paradox).
- **Hash the long URL (e.g. MD5, take first 7 chars)**: deterministic,
  but still needs collision handling since truncated hashes can collide.
- **Base62 of auto-increment ID (chosen)**: zero collision risk by
  construction — the DB already guarantees unique IDs. Downside: codes
  are sequential and guessable, which leaks approximate volume
  (competitors could estimate how many URLs you've shortened) and could
  be a minor enumeration risk if that mattered for the use case.

For a v1 learning project this trade-off is fine and worth being able to
articulate — a production system serving a public product would likely
add a random salt or shuffle step to avoid sequential codes.

## 4. Current architecture (v1)

```
Client -> FastAPI app -> SQLite
```

Single process, single file-based DB. No caching, no load balancing.
This will not survive the read traffic estimated above — that's expected
and intentional; v1 exists to get the core logic correct before adding
infrastructure complexity.

## 5. Planned architecture (v2+)

```
Client -> Load Balancer -> [App instance 1, App instance 2, ...] -> Redis (cache) -> Postgres
```

**Why Redis in front of Postgres, not instead of it:**
Redis is in-memory — fast, but not durable by default and expensive to
scale to the full 3.6 TB dataset. Postgres remains the source of truth;
Redis holds the hot subset (recently/frequently accessed short codes) so
most redirect reads never hit the DB at all.

**Cache invalidation approach:** Since long_url never changes once a
short_code is created (URLs in this system are immutable), there's no
invalidation problem to solve here — a genuinely simple case, and worth
saying explicitly in an interview since cache invalidation is usually the
hard part of caching.

**Why Postgres over SQLite at scale:** SQLite locks the entire file on
writes, which won't hold up under concurrent write load or multiple app
instances. Postgres supports proper concurrent access and, later,
read replicas if reads still bottleneck after caching.

## 6. Open questions / things to test empirically (not just assume)

- At what request rate does SQLite actually start failing? (Answer this
  with `locust` load testing in v5, don't just assume from reading.)
- How much does adding Redis actually reduce DB load, measured, not
  theorized?
- What's the real click-count-update contention look like under
  concurrent load? (Every redirect writes to increment click_count —
  this could become a write bottleneck even though redirects are
  conceptually a "read" path.)
