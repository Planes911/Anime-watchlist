"""Watched/review endpoints: validation rules and per-user isolation."""

REVIEW = {"animeId": 1, "rating": 5, "review": "Animenya luar biasa"}


def test_log_watched_and_list(client, user_a):
    r = client.post("/api/watched", json=REVIEW, headers=user_a)
    assert r.status_code == 201
    body = r.json()
    assert body["rating"] == 5 and body["review"] == "Animenya luar biasa"
    assert body["anime"]["title"] == "Fullmetal Alchemist: Brotherhood"

    listed = client.get("/api/watched", headers=user_a).json()
    assert len(listed) == 1 and listed[0]["anime_id"] == 1


def test_accepts_opinion_alias_sent_by_frontend(client, user_a):
    payload = {"anime_id": 2, "animeId": 2, "rating": 4, "opinion": "Seru", "review": "Seru"}
    assert client.post("/api/watched", json=payload, headers=user_a).status_code == 201


def test_rating_must_be_integer_1_to_5(client, user_a):
    for bad in (0, 6, -1, 4.5):
        r = client.post("/api/watched", json={**REVIEW, "rating": bad}, headers=user_a)
        assert r.status_code == 400, bad


def test_review_must_not_be_blank(client, user_a):
    assert client.post("/api/watched", json={**REVIEW, "review": ""}, headers=user_a).status_code == 400
    assert client.post("/api/watched", json={**REVIEW, "review": "    "}, headers=user_a).status_code == 400


def test_unknown_anime_is_404(client, user_a):
    assert client.post("/api/watched", json={**REVIEW, "animeId": 9999}, headers=user_a).status_code == 404


def test_logging_same_anime_twice_is_409(client, user_a):
    assert client.post("/api/watched", json=REVIEW, headers=user_a).status_code == 201
    assert client.post("/api/watched", json=REVIEW, headers=user_a).status_code == 409


def test_watched_is_private_per_user(client, user_a, user_b):
    client.post("/api/watched", json=REVIEW, headers=user_a)
    assert client.get("/api/watched", headers=user_b).json() == []
    # another user may review the same anime (uniqueness is per user+anime PAIR)
    assert client.post("/api/watched", json=REVIEW, headers=user_b).status_code == 201
