from app.core.security import create_access_token, decode_token, get_password_hash, verify_password


def test_password_hashing():
    pwd = "EnterpriseSecret123!"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_flow():
    payload = {"sub": "user-uuid-123", "email": "test@certverify.ai", "role": "USER"}
    token = create_access_token(payload)
    assert isinstance(token, str)
    decoded = decode_token(token)
    assert decoded["sub"] == "user-uuid-123"
    assert decoded["email"] == "test@certverify.ai"
    assert decoded["role"] == "USER"

