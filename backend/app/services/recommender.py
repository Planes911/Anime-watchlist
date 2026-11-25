"""Rule-based anime recommendations: no external API, deterministic and easy to test."""

from collections import Counter

LIKED_MIN_RATING = 4  # reviews with this rating or higher define the user's taste
GENRE_WEIGHT = 0.60
STUDIO_WEIGHT = 0.15
RATING_WEIGHT = 0.25

def build_profile(liked: list[dict]) -> tuple[Counter, set[str]]:
    raw: Counter = Counter()
    studios: set[str] = set()
    for item in liked:
        weight = item["user_rating"] / 5  # a 5-star review counts more than a 4-star one
        for genre in item["genres"]:
            raw[genre] += weight
        studios.add(item["studio"])
    top = max(raw.values(), default=1)
    return Counter({genre: w / top for genre, w in raw.items()}), studios

def _top_rated(candidates: list[dict], limit: int, reason: str) -> list[dict]:
    best = sorted(candidates, key=lambda c: (-c["rating"], c["id"]))[:limit]
    return [{"anime_id": c["id"], "score": round(c["rating"] / 10, 3), "reason": reason} for c in best]

def _reason(candidate: dict, liked: list[dict]) -> str:
    genres = set(candidate["genres"])
    source = max(
        liked,
        key=lambda item: (len(genres & set(item["genres"])), item["studio"] == candidate["studio"], item["user_rating"]),
    )
    shared = [g for g in candidate["genres"] if g in source["genres"]]
    details = []
    if shared:
        details.append("genre sama: " + ", ".join(shared[:3]))
    if source["studio"] == candidate["studio"]:
        details.append("studio sama: " + candidate["studio"])
    suffix = f" ({'; '.join(details)})" if details else ""
    return f"Karena kamu menyukai {source['title']}{suffix}"

def recommend(liked: list[dict], candidates: list[dict], limit: int = 5) -> list[dict]:
    fallback_reason = "Anime dengan rating tertinggi yang belum kamu tonton."
    if not liked:
        return _top_rated(candidates, limit, fallback_reason)

    genre_profile, studios = build_profile(liked)
    scored = []
    for c in candidates:
        genre_score = sum(genre_profile.get(g, 0) for g in c["genres"]) / len(c["genres"]) if c["genres"] else 0.0
        studio_score = 1.0 if c["studio"] in studios else 0.0
        if genre_score == 0 and studio_score == 0:
            continue  # nothing in common with this user's taste
        score = GENRE_WEIGHT * genre_score + STUDIO_WEIGHT * studio_score + RATING_WEIGHT * (c["rating"] / 10)
        scored.append((score, c))

    scored.sort(key=lambda pair: (-pair[0], -pair[1]["rating"], pair[1]["id"]))
    results = [
        {"anime_id": c["id"], "score": round(score, 3), "reason": _reason(c, liked)}
        for score, c in scored[:limit]
    ]
    return results or _top_rated(candidates, limit, fallback_reason)