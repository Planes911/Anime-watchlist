"""Password hashing (bcrypt) and JWT helpers."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

# bcrypt silently ignores everything after 72 bytes, so longer passwords are rejected explicitly.
_MAX_BCRYPT_BYTES = 72

# Hash of a throwaway password. Verifying against it when the email is unknown keeps the response
# time similar, so attackers cannot discover registered emails by timing login attempts.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(rounds=4)).decode()

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    data = password.encode("utf-8")
    # Such a password could never have been registered, so it cannot match.
    if len(data) > _MAX_BCRYPT_BYTES:
        return False
    try:
        return bcrypt.checkpw(data, hashed.encode("utf-8"))
    except ValueError:
        return False
    
def burn_time_like_a_real_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)
    
def create_access_token(user_id: int) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        # 'sub' (subject) carries the user id; the JWT spec requires it to be a string.
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=s.jwt_expire_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)

def decode_access_token(token: str) -> int:
    s = get_settings()
    payload = jwt.decode(
        token,
        s.jwt_secret,
        # Whitelist the algorithm so tokens using 'alg: none' or any other algorithm are rejected.
        algorithms=[s.jwt_algorithm],
        # Reject tokens that carry no expiry or no subject.
        options={"require": ["exp", "sub"]},
    )
    return int(payload["sub"])