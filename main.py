"""
main.py
URL Shortener API - v1

Endpoints (versioned under /v1/url — see DESIGN.md for why we version):
  POST /v1/url               -> create a short URL (optionally with a custom code)
  GET  /v1/url/{shorturl}    -> redirect to the original URL
  GET  /v1/url/{shorturl}/stats -> see click count + metadata

Run with: uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional

from database import init_db, get_connection
from encoder import encode

app = FastAPI(title="URL Shortener", version="1.0.0")


@app.on_event("startup")
def startup():
    init_db()


class ShortenRequest(BaseModel):
    long_url: HttpUrl
    custom_url: Optional[str] = None  # user can request their own short code


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    long_url: str


@app.post("/v1/url", response_model=ShortenResponse)
def create_short_url(payload: ShortenRequest):
    long_url = str(payload.long_url)

    with get_connection() as conn:
        # --- Case 1: user asked for a custom short code ---
        if payload.custom_url:
            custom_code = payload.custom_url

            # someone else might already be using this exact code - must check
            taken = conn.execute(
                "SELECT id FROM urls WHERE short_code = ?", (custom_code,)
            ).fetchone()
            if taken:
                raise HTTPException(
                    status_code=409,
                    detail=f"Custom code '{custom_code}' is already taken",
                )

            conn.execute(
                "INSERT INTO urls (long_url, short_code) VALUES (?, ?)",
                (long_url, custom_code),
            )
            conn.commit()
            code = custom_code

        # --- Case 2: no custom code, auto-generate one ---
        else:
            # dedup: if this exact long_url was already shortened
            # (without a custom code), reuse that code instead of
            # creating a duplicate row.
            existing = conn.execute(
                "SELECT short_code FROM urls WHERE long_url = ?", (long_url,)
            ).fetchone()

            if existing:
                code = existing["short_code"]
            else:
                cursor = conn.execute(
                    "INSERT INTO urls (long_url, short_code) VALUES (?, ?)",
                    (long_url, ""),  # placeholder until we have the auto-increment id
                )
                new_id = cursor.lastrowid
                code = encode(new_id)

                conn.execute(
                    "UPDATE urls SET short_code = ? WHERE id = ?", (code, new_id)
                )
                conn.commit()

    return ShortenResponse(
        short_code=code,
        short_url=f"http://localhost:8000/v1/url/{code}",
        long_url=long_url,
    )


@app.get("/v1/url/{shorturl}")
def redirect_to_url(shorturl: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT long_url FROM urls WHERE short_code = ?", (shorturl,)
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Short URL not found")

        # increment click count - this is our "hot write path"
        conn.execute(
            "UPDATE urls SET click_count = click_count + 1 WHERE short_code = ?",
            (shorturl,),
        )
        conn.commit()

    return RedirectResponse(url=row["long_url"])


@app.get("/v1/url/{shorturl}/stats")
def get_stats(shorturl: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT long_url, short_code, created_at, click_count FROM urls WHERE short_code = ?",
            (shorturl,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Short URL not found")

    return dict(row)
