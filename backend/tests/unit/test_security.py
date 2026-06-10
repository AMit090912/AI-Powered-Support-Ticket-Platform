from app.core import security


def test_password_hash_roundtrip():
    hashed = security.hash_password("s3cret")
    assert hashed != "s3cret"
    assert security.verify_password("s3cret", hashed) is True
    assert security.verify_password("wrong", hashed) is False


def test_jwt_encode_decode_roundtrip():
    token = security.create_access_token({"sub": "5", "role": "agent"})
    payload = security.decode_token(token)
    assert payload["sub"] == "5"
    assert payload["role"] == "agent"


def test_decode_invalid_token_returns_none():
    assert security.decode_token("not.a.jwt") is None
