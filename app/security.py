import hmac
import hashlib


def verify_signature(
    raw_body: bytes,
    header: str | None,
    secret: str
) -> bool:

    if not header or not header.startswith("sha256="):
        return False

    expected = (
        "sha256="
        + hmac.new(
            secret.encode(),
            raw_body,
            hashlib.sha256
        ).hexdigest()
    )

    return hmac.compare_digest(expected, header)

# Check: write a pytest test that signs a fake body with your secret 
# and expects True, then changes one byte and expects False.

# use hmac.compare_digest(expected, header) instead of expected == header
# to avoid timing attacks. 
# A normal string comparison can potentially take slightly different amounts of time depending on how much of the strings matches.
# compare_digest() is designed for comparing sensitive values such as cryptographic signatures without that kind of timing leakage.
# You don't need to implement the cryptography yourself. Python's standard library handles it.