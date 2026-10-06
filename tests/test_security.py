import hmac
import hashlib

from app.security import verify_signature


def create_signature(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()


# test 01
# body
#  ↓
# sign with secret
#  ↓
# signature
#  ↓
# verify same body + same secret
#  ↓
# True

def test_valid_signature():
    secret = "test-secret"
    body = b'{"action":"opened"}'

    signature = create_signature(body, secret)

    assert verify_signature(
        body,
        signature,
        secret
    ) is True


# test 02
# original body
#  ↓
# sign it
#  ↓
# signature

# THEN

# change one thing in body
#  ↓
# verify using old signature
#  ↓
# False
def test_invalid_signature_when_body_changes():
    secret = "test-secret"
    body = b'{"action":"opened"}'

    signature = create_signature(body, secret)

    changed_body = b'{"action":"closed"}'

    assert verify_signature(
        changed_body,
        signature,
        secret
    ) is False