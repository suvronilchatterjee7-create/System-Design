"""
encoder.py
Base62 encoding: turns an integer ID into a short alphanumeric string.

Why base62 instead of random strings?
- Deterministic: same ID always -> same code, no collision-checking needed
- Dense: 62 characters (a-z, A-Z, 0-9) means short codes even for huge IDs
  e.g. ID 1,000,000,000 -> only 6 characters
- We rely on the DB's auto-increment ID being unique, so the code is
  automatically unique too. This trades "unpredictable codes" for
  simplicity - a fine trade-off for a learning project (note this as a
  known limitation in your design doc: codes are guessable/sequential).
"""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)  # 62


def encode(num: int) -> str:
    """Convert a positive integer into a base62 string."""
    if num == 0:
        return ALPHABET[0]

    digits = []
    while num > 0:
        num, remainder = divmod(num, BASE)
        digits.append(ALPHABET[remainder])

    return "".join(reversed(digits))


def decode(short_code: str) -> int:
    """Convert a base62 string back into an integer. (Not strictly needed
    for this project since we look up by short_code directly, but useful
    for debugging / future use.)"""
    num = 0
    for char in short_code:
        num = num * BASE + ALPHABET.index(char)
    return num
