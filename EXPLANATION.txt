# What This Project Actually Is — A Plain-Language Walkthrough

This file exists to answer one question clearly: **what have we actually
built, what does it do when it runs, and what is it NOT (yet)?**

---

## Is this a real website?

**No.** There is no page you can open in a browser with an input box and
a "Shorten" button. What we built is a **backend API** — a program that
sits and waits for requests, and sends back a response. It has no visual
interface at all.

Think of it like a vending machine with no front panel — just the
mechanism inside that takes coins and dispenses items. You interact with
it by sending it exact, structured requests (currently via `curl` or the
`/docs` testing page), not by clicking buttons on a webpage. A real
consumer-facing website would need two more things added on top of what
exists now:

1. **A frontend** — an actual webpage with an input box, a button, and
   some JavaScript that sends a request to this API when clicked.
2. **Deployment** — hosting this program on a server that's reachable
   from the public internet, with a real domain name. Right now it only
   runs on your own machine (`localhost`), reachable only by you.

Neither of these exists yet. What exists is the **engine** — the actual
logic of how a URL gets shortened, stored, and looked back up. That's
the part with real system design substance; the frontend and deployment
are separate, more mechanical pieces of work that can be added later.

---

## So what does `main.py` actually do when you run it?

When you run `uvicorn main:app --reload`, here's what happens, in order:

1. **The server starts up** and creates the database table if it doesn't
   already exist (this is the `startup` function calling `init_db()`).
2. **It waits.** Nothing happens until someone sends it a request. It's
   not "running" in the sense of doing continuous work — it's idle,
   listening, the way a phone sits idle until it rings.
3. **When a request arrives**, `main.py` looks at two things: the HTTP
   method (`POST` or `GET`) and the path (`/v1/url`, `/v1/url/{code}`,
   etc.) to decide which function should handle it.

Let's walk through each function concretely.

### `create_short_url()` — handles `POST /v1/url`

This runs when someone wants to shorten a URL. Step by step:

1. FastAPI automatically checks that the incoming request has a valid
   `long_url` (and optionally a `custom_url`) — this validation happens
   because of the `ShortenRequest` class, before our code even runs. If
   the request is malformed, FastAPI rejects it automatically.
2. **If a `custom_url` was provided:** check the database — is this
   exact code already in use? If yes, reject with a `409 Conflict`
   error. If no, save the new row using that custom code directly.
3. **If no `custom_url` was provided:** check if this exact long URL was
   already shortened before. If yes, just return the existing short
   code (no duplicate created). If no, insert a new row, get back the
   auto-generated database ID, convert that ID into a short code using
   base62 encoding, then save that code onto the row.
4. Send back a response containing the short code and the full short
   URL.

### `redirect_to_url()` — handles `GET /v1/url/{shorturl}`

This runs when someone "clicks" a short link (or, right now, when a
request is manually sent to that path). Step by step:

1. Look up the database — is there a row where `short_code` matches
   what was requested?
2. If not found, return a `404 Not Found` error.
3. If found, increment that row's `click_count` by 1 — this is how we
   track popularity.
4. Send back a `RedirectResponse`. This is a special kind of response
   that tells whatever sent the request "go here instead" — in a real
   browser, this is what would cause an automatic jump to the original
   long URL. Since we're not using a browser yet, `curl` just shows us
   the raw redirect instruction instead of following it automatically.

### `get_stats()` — handles `GET /v1/url/{shorturl}/stats`

A simple read-only lookup — finds the row matching the given short code
and returns its long URL, creation time, and click count. No writes
happen here at all.

---

## Why "no visible website" is actually fine for this stage

In real engineering teams, backend and frontend are frequently built and
tested completely separately — the backend engineer builds and verifies
the API works correctly using tools like `curl` or Postman *before* any
UI exists, exactly like we did here. The interactive `/docs` page FastAPI
gives you for free is also a legitimate way developers test APIs without
writing a single line of frontend code.

The core, hardest-to-get-right part of a URL shortener isn't the button
— it's exactly what we spent our time on: the encoding scheme, the
database schema, the collision handling, and the API contract. A
frontend is comparatively mechanical once the backend logic is solid.

---

## If you want to make this feel like a real, visitable website next

Two separate additions, each optional and independent of the other:

- **Add a frontend**: a single HTML page with an input box and a button
  that calls `POST /v1/url` using JavaScript, and displays the result.
  This alone would let you interact with the project in a browser.
- **Deploy it**: put this running program on a cloud host (e.g. Render,
  Railway, Fly.io — many have free tiers) so it has a real, public URL
  instead of only running on your own machine. At that point, and only
  at that point, it becomes something you could actually share with
  someone else to try.

Neither of these changes the core logic we already built — they're
additive layers on top of a backend that already works correctly.
