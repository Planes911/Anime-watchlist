"""Rule-based recommendations: scoring unit tests plus the authenticated endpoint."""

from app.services.recommender import build_profile, recommend

STEINS_GATE = 8
CODE_GEASS = 14  # shares Sci-Fi and Drama with Steins;Gate


def _liked(title="A", genres=("Sci-Fi",), studio="S", user_rating=5):
    return {"title": title, "genres": list(genres), "studio": studio, "user_rating": user_rating}


def _cand(id, genres, studio="X", rating=8.0, title=None):
    return {"id": id, "title": title or f"T{id}", "genres": list(genres), "studio": studio, "rating": rating}


# --- unit tests (no database) ---------------------------------------------------------------

def test_profile_weights_are_scaled_to_one():
    genres, studios = build_profile([_liked(genres=("Sci-Fi", "Drama"), user_rating=5), _liked(genres=("Sci-Fi",), user_rating=4)])
    assert genres["Sci-Fi"] == 1.0 and 0 < genres["Drama"] < 1.0
    assert studios == {"S"}


def test_no_history_falls_back_to_top_rated():
    result = recommend([], [_cand(1, ["A"], rating=7), _cand(2, ["B"], rating=9), _cand(3, ["C"], rating=8)], limit=2)
    assert [r["anime_id"] for r in result] == [2, 3]


def test_genre_match_beats_unrelated_anime():
    result = recommend([_liked(genres=("Sci-Fi",))], [_cand(1, ["Romance"], rating=9.9), _cand(2, ["Sci-Fi"], rating=7.0)])
    assert [r["anime_id"] for r in result] == [2]  # the Romance anime has nothing in common


def test_same_studio_alone_is_enough_to_match():
    result = recommend([_liked(studio="Bones")], [_cand(1, ["Romance"], studio="Bones")])
    assert [r["anime_id"] for r in result] == [1]
    assert "studio sama: Bones" in result[0]["reason"]


def test_results_are_sorted_limited_and_deterministic():
    candidates = [_cand(i, ["Sci-Fi"], rating=8.0) for i in (3, 1, 2)]
    first = recommend([_liked()], candidates, limit=2)
    assert [r["anime_id"] for r in first] == [1, 2]  # equal scores: lower id first
    assert first == recommend([_liked()], list(reversed(candidates)), limit=2)
    assert first[0]["score"] >= first[1]["score"]


def test_reason_mentions_the_liked_anime_and_shared_genres():
    result = recommend([_liked(title="Steins;Gate", genres=("Sci-Fi", "Drama"))], [_cand(1, ["Drama", "Sci-Fi", "Action"])])
    assert result[0]["reason"] == "Karena kamu menyukai Steins;Gate (genre sama: Drama, Sci-Fi)"


# --- endpoint tests -------------------------------------------------------------------------

def _review(client, headers, anime_id, rating):
    r = client.post("/api/watched", json={"animeId": anime_id, "rating": rating, "review": "ok"}, headers=headers)
    assert r.status_code == 201, r.text


def test_without_history_returns_top_rated(client, user_a):
    recs = client.get("/api/recommendations", headers=user_a).json()
    assert len(recs) == 5
    scores = [r["score"] for r in recs]
    assert scores == sorted(scores, reverse=True)
    assert set(recs[0]) == {"anime", "score", "reason"} and "rating tertinggi" in recs[0]["reason"]


def test_recommendations_follow_liked_anime(client, user_a):
    _review(client, user_a, STEINS_GATE, 5)
    recs = client.get("/api/recommendations", headers=user_a).json()
    ids = [r["anime"]["id"] for r in recs]
    assert STEINS_GATE not in ids  # already watched
    assert ids[0] == CODE_GEASS
    assert all("Steins;Gate" in r["reason"] for r in recs)


def test_low_rated_anime_does_not_shape_taste(client, user_a):
    _review(client, user_a, STEINS_GATE, 2)
    recs = client.get("/api/recommendations", headers=user_a).json()
    assert all("rating tertinggi" in r["reason"] for r in recs)
    assert STEINS_GATE not in [r["anime"]["id"] for r in recs]


def test_skips_watchlist_and_progress_entries(client, user_a):
    _review(client, user_a, STEINS_GATE, 5)
    client.post("/api/watchlist", json={"animeId": CODE_GEASS}, headers=user_a)
    ids = [r["anime"]["id"] for r in client.get("/api/recommendations", params={"limit": 20}, headers=user_a).json()]
    assert CODE_GEASS not in ids
    client.put("/api/progress/4", json={"status": "watching", "currentEpisode": 1}, headers=user_a)
    ids = [r["anime"]["id"] for r in client.get("/api/recommendations", params={"limit": 20}, headers=user_a).json()]
    assert 4 not in ids


def test_recommendations_are_per_user(client, user_a, user_b):
    _review(client, user_a, STEINS_GATE, 5)
    recs_b = client.get("/api/recommendations", headers=user_b).json()
    assert all("rating tertinggi" in r["reason"] for r in recs_b)  # B has no history of their own


def test_limit_is_validated(client, user_a):
    assert client.get("/api/recommendations", params={"limit": 0}, headers=user_a).status_code == 400
    assert client.get("/api/recommendations", params={"limit": 21}, headers=user_a).status_code == 400
    assert len(client.get("/api/recommendations", params={"limit": 3}, headers=user_a).json()) == 3
