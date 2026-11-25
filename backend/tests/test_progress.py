"""Watch-progress endpoints: upsert rules, validation and per-user isolation."""

STEINS_GATE = 8  # 24 episodes in the seed data
FILM = 6         # Spirited Away: a single film, 1 episode


def put(client, headers, anime_id=STEINS_GATE, **body):
    return client.put(f"/api/progress/{anime_id}", json=body, headers=headers)


def test_set_progress_creates_then_updates(client, user_a):
    r = put(client, user_a, status="watching", currentEpisode=5)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "watching" and body["current_episode"] == 5
    assert body["total_episodes"] == 24 and body["anime"]["title"] == "Steins;Gate"

    assert put(client, user_a, status="watching", currentEpisode=9).json()["current_episode"] == 9
    assert len(client.get("/api/progress", headers=user_a).json()) == 1  # updated, not duplicated


def test_accepts_snake_case_current_episode_too(client, user_a):
    assert put(client, user_a, status="watching", current_episode=3).status_code == 200


def test_completed_moves_counter_to_last_episode(client, user_a):
    body = put(client, user_a, status="completed", currentEpisode=2).json()
    assert body["status"] == "completed" and body["current_episode"] == 24


def test_episode_cannot_exceed_total(client, user_a):
    assert put(client, user_a, status="watching", currentEpisode=25).status_code == 400
    assert put(client, user_a, anime_id=FILM, status="watching", currentEpisode=2).status_code == 400
    assert put(client, user_a, status="watching", currentEpisode=24).status_code == 200


def test_invalid_body_is_400(client, user_a):
    assert put(client, user_a, status="watching", currentEpisode=-1).status_code == 400
    assert put(client, user_a, status="binge", currentEpisode=1).status_code == 400
    assert put(client, user_a, status="watching").status_code == 400
    assert put(client, user_a, status="watching", currentEpisode=1.5).status_code == 400


def test_unknown_anime_is_404_and_bad_id_is_400(client, user_a):
    assert put(client, user_a, anime_id=9999, status="watching", currentEpisode=1).status_code == 404
    assert put(client, user_a, anime_id="abc", status="watching", currentEpisode=1).status_code == 400


def test_filter_by_status(client, user_a):
    put(client, user_a, anime_id=1, status="watching", currentEpisode=10)
    put(client, user_a, anime_id=2, status="dropped", currentEpisode=3)
    watching = client.get("/api/progress", params={"status": "watching"}, headers=user_a).json()
    assert [p["anime_id"] for p in watching] == [1]
    assert client.get("/api/progress", params={"status": "nope"}, headers=user_a).status_code == 400


def test_progress_is_private_per_user(client, user_a, user_b):
    put(client, user_a, status="watching", currentEpisode=5)
    assert client.get("/api/progress", headers=user_b).json() == []
    # B gets an independent entry for the same anime.
    assert put(client, user_b, status="on_hold", currentEpisode=1).status_code == 200
    assert client.get("/api/progress", headers=user_a).json()[0]["status"] == "watching"


def test_delete_progress(client, user_a, user_b):
    put(client, user_a, status="watching", currentEpisode=5)
    assert client.delete(f"/api/progress/{STEINS_GATE}", headers=user_b).status_code == 404  # not B's entry
    assert client.delete(f"/api/progress/{STEINS_GATE}", headers=user_a).status_code == 200
    assert client.get("/api/progress", headers=user_a).json() == []
    assert client.delete(f"/api/progress/{STEINS_GATE}", headers=user_a).status_code == 404
