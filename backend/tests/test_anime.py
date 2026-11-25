"""Anime catalogue endpoints: listing, filtering, searching and detail."""

def test_list_animes_returns_seeded_20_with_contract_shape(client):
    r = client.get("/api/anime")
    assert r.status_code == 200
    animes = r.json()
    assert len(animes) == 20
    first = animes[0]
    assert set(first) == {"id", "title", "year", "studio", "genres", "rating",
                          "episodes", "synopsis", "poster_url", "cast", "total_episodes"}
    assert isinstance(first["genres"], list) and isinstance(first["cast"], list)


def test_filter_by_genre_is_case_insensitive(client):
    animes = client.get("/api/anime", params={"genre": "sci-fi"}).json()
    assert animes
    assert all("Sci-Fi" in m["genres"] for m in animes)


def test_search_matches_title_and_studio(client):
    assert [m["title"] for m in client.get("/api/anime", params={"search": "fullmetal"}).json()] == ["Fullmetal Alchemist: Brotherhood"]
    by_studio = client.get("/api/anime", params={"search": "bones"}).json()
    assert by_studio and all("Bones" in m["studio"] for m in by_studio)


def test_search_treats_like_wildcards_as_plain_text(client):
    assert client.get("/api/anime", params={"search": "%"}).json() == []


def test_shuffle_keeps_same_animes(client):
    plain = {m["id"] for m in client.get("/api/anime").json()}
    shuffled = {m["id"] for m in client.get("/api/anime", params={"shuffle": "true"}).json()}
    assert plain == shuffled


def test_get_anime_detail(client):
    r = client.get("/api/anime/8")
    assert r.status_code == 200
    assert r.json()["title"] == "Steins;Gate"


def test_unknown_anime_is_404_and_bad_id_is_400(client):
    r = client.get("/api/anime/9999")
    assert r.status_code == 404
    assert "message" in r.json()
    assert client.get("/api/anime/abc").status_code == 400
