"""Unit tests for pure functions: password hashing, LLM answer parsing, the seeder."""
import pytest
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Anime
from app.security import hash_password, verify_password
from app.seed import load_animes_json, seed_animes


def test_password_hashing_uses_unique_salt_and_verifies():
    h1, h2 = hash_password("password123"), hash_password("password123")
    assert h1 != h2  # random salt
    assert verify_password("password123", h1)
    assert not verify_password("password124", h1)
    assert not verify_password("x" * 73, h1)  # more than 72 bytes is rejected, not a crash

def test_seeder_is_idempotent():
    with SessionLocal() as db:  # the autouse fixture already seeded once
        assert seed_animes(db, load_animes_json()) == 0
        assert db.scalar(select(func.count()).select_from(Anime)) == 20
