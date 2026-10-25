"""Hash e verificação da senha de autorização do adulto."""

from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 200_000
SALT_BYTES = 16
MAX_ITERATIONS = 1_000_000


def hash_password(
    password: str,
    *,
    salt: bytes | None = None,
    iterations: int = ITERATIONS,
) -> str:
    """Gera um hash com salt aleatório no formato algoritmo$iterações$salt$hash."""
    salt = salt if salt is not None else secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return f"{ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Confere uma senha contra um hash gerado por `hash_password`."""
    try:
        algorithm, raw_iterations, salt_hex, digest_hex = encoded.split("$", 3)
        iterations = int(raw_iterations)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (AttributeError, TypeError, ValueError):
        return False
    if algorithm != ALGORITHM or not 1 <= iterations <= MAX_ITERATIONS:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate, expected)
