"""Application entry point: wires up CORS, error handlers and routers."""

from fastapi import FastAPI

from app.config import get_settings
from app.errors import register_exception_handlers
from app.routers import anime, auth, watchlist, watched, progress, recommendations

# Fails fast at startup if required settings (e.g. JWT_SECRET) are missing.
settings = get_settings()

app = FastAPI(
    title="AnimeLog API",
    version="1.0.0",
    description="REST API watchlist & review anime dengan rekomendasi Gemini (grounded ke database lokal).",
)

# Uniform JSON error format for every failure.
register_exception_handlers(app)

# Every router must be registered here; otherwise its endpoints answer 404.
app.include_router(auth.router)
app.include_router(anime.router)
app.include_router(watchlist.router)
app.include_router(watched.router)
app.include_router(progress.router)
app.include_router(recommendations.router)

@app.get("/api/health", tags=["Meta"])
def health():
    """Lightweight liveness probe (does not touch the database)."""
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
def root():
    """Landing route so the bare URL is not a 404."""
    return {"name": "AnimeLog API", "docs": "/docs", "health": "/api/health"}