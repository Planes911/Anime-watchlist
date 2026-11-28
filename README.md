# AnimeLog API — Anime Watchlist, Progress & Review Backend

REST API for **AnimeLog**, an anime tracking platform simmilar to MyAnimeList. Users register, build a personal
watchlist, track which episode they are on, log finished anime with a rating and a review, and get
**recommendations computed from their own taste** with no external AI service involved.

- **Live API:** <https://anime-watchlist-amber.vercel.app/> — health check at `/api/health`
- **Swagger UI:** <https://anime-watchlist-amber.vercel.app/docs>
- **Postman documentation:** <https://ramadhan-mukti-putra-s-team.docs.buildwithfern.com/anime-log-api/introduction>

## Features

- **Authentication** with JWT; passwords are hashed with bcrypt.
- **Anime catalogue** with genre filter, text search and shuffle (20 seeded titles).
- **Watchlist**: save anime you plan to watch.
- **Watch progress**: track `watching`, `completed`, `on_hold` or `dropped` together with the current episode.
- **Watched log**: one rating (1–5) and review per user and anime.
- **Rule-based recommendations** from the anime you rated highly, with a human-readable reason for each pick.
- Uniform JSON error format, input validation, and an automated test suite.

## Tech stack

Python 3.11+ (developed on 3.13) · FastAPI · SQLAlchemy 2.0 · PostgreSQL on Supabase (SQLite for local development
and tests) · bcrypt · PyJWT · pytest · Postman

## Project structure

```text
.
├── data/
│   ├── anime.json            # 20 initial anime used by the seeder
│   └── seed.sql              # the same data as plain SQL (reference)
├── docs/
│   ├── postman/              # Postman collection and environment (exported)
│   └── images/               # screenshots used in this README
└── backend/
    ├── app/
    │   ├── main.py           # entry point: CORS, error handlers, routers
    │   ├── config.py         # settings loaded from environment variables
    │   ├── database.py       # engine and session factory
    │   ├── models.py         # database schema (see the ERD below)
    │   ├── schemas.py        # request/response validation (Pydantic)
    │   ├── security.py       # bcrypt password hashing + JWT helpers
    │   ├── deps.py           # authentication dependency
    │   ├── errors.py         # uniform error format
    │   ├── seed.py           # table creation + idempotent seeder
    │   ├── routers/          # auth, anime, watchlist, watched, progress, recommendations
    │   └── services/         # recommender.py (scoring logic, no database or framework code)
    ├── tests/                # pytest suite
    ├── .env.example          # template for local configuration
    ├── pytest.ini
    └── requirements.txt
```

## Getting started

### Prerequisites

- Python 3.11 or newer
- A database, either of these:
  - **SQLite**: nothing to install, this is the default.
  - **PostgreSQL**: for example a free [Supabase](https://supabase.com) project.

### Install and run

Run these commands from the `backend/` folder.

```bash
cd backend
python -m venv .venv

source .venv/bin/activate          # macOS/Linux
.venv\Scripts\activate             # Windows (PowerShell)

pip install -r requirements.txt

cp .env.example .env               # Windows: copy .env.example .env
                                   # now open .env and fill in the values

python -m app.seed                 # creates the tables and inserts the 20 anime (safe to re-run)
uvicorn app.main:app --reload --port 8000
```

The API is now available at <http://localhost:8000> and the Swagger UI at <http://localhost:8000/docs>.

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Required in production | `postgresql://user:pass@host:port/db` or `sqlite:///./animelog.db`. Defaults to a local SQLite file. `postgres://` and `postgresql://` URLs are converted automatically for the psycopg driver. |
| `JWT_SECRET` | **Yes** | Secret used to sign tokens, at least 16 characters. The app refuses to start without it. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `JWT_EXPIRE_MINUTES` | No | Token lifetime. Default `1440` (24 hours). |
| `BCRYPT_ROUNDS` | No | bcrypt cost factor. Default `12`; the test suite lowers it to keep tests fast. |

### Running the tests

```bash
cd backend
pytest -v
```

The suite uses an in-memory SQLite database, so it needs no internet connection or external service. The test
configuration overrides `DATABASE_URL`, so the tests can never touch your real (for example Supabase) database.

## API reference

Protected endpoints expect the header `Authorization: Bearer <token>`, where the token comes from `POST /api/auth/login`.

| Method & path | Auth | Success | Error codes |
|---|---|---|---|
| `POST /api/auth/register` | – | 201 | 400, 409 |
| `POST /api/auth/login` | – | 200 `{token, token_type, user}` | 400, 401 |
| `GET /api/anime?genre=&search=&shuffle=` | – | 200 | 400 |
| `GET /api/anime/{id}` | – | 200 | 400, 404 |
| `GET /api/watchlist` | Bearer | 200 | 401 |
| `POST /api/watchlist` | Bearer | 201 | 400, 401, 404, 409 |
| `DELETE /api/watchlist/{animeId}` | Bearer | 200 | 400, 401, 404 |
| `GET /api/watched` | Bearer | 200 | 401 |
| `POST /api/watched` | Bearer | 201 | 400, 401, 404, 409 |
| `GET /api/progress?status=` | Bearer | 200 | 400, 401 |
| `PUT /api/progress/{animeId}` | Bearer | 200 | 400, 401, 404 |
| `DELETE /api/progress/{animeId}` | Bearer | 200 | 400, 401, 404 |
| `GET /api/recommendations?limit=` | Bearer | 200 | 400, 401 |
| `GET /api/health` | – | 200 | – |

## Error format

Every error, expected or not, uses the same JSON shape:

```json
{ "error": "Conflict", "message": "Anime sudah ada di watchlist kamu.", "status": 409 }
```

Validation errors use status **400** (not FastAPI's default 422) and add a `details` array:

```json
{
  "error": "Bad Request",
  "message": "Validasi gagal - rating: Input should be less than or equal to 5",
  "status": 400,
  "details": [{ "field": "rating", "message": "Input should be less than or equal to 5" }]
}
```

### Example requests

```bash
# Register, then log in
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"andi","email":"andi@mail.com","password":"secret1234"}'

curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"andi@mail.com","password":"secret1234"}'

# Use the returned token
curl http://localhost:8000/api/watchlist -H "Authorization: Bearer <token>"

# Track progress: episode 5 of anime 8
curl -X PUT http://localhost:8000/api/progress/8 \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"status":"watching","currentEpisode":5}'

# Log a finished anime, then ask for recommendations
curl -X POST http://localhost:8000/api/watched \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"animeId":8,"rating":5,"review":"Seru banget"}'

curl "http://localhost:8000/api/recommendations?limit=3" -H "Authorization: Bearer <token>"
```

A recommendation looks like this (the `anime` object is shortened here):

```json
{
  "anime": { "id": 14, "title": "Code Geass: Lelouch of the Rebellion", "...": "..." },
  "score": 0.617,
  "reason": "Karena kamu menyukai Steins;Gate (genre sama: Sci-Fi, Drama)"
}
```

On Windows PowerShell, `curl` is an alias of `Invoke-WebRequest`; use `curl.exe` or the Swagger UI at `/docs` instead.

## API documentation and testing

Three layers document and verify the API:

1. **Swagger UI** at `/docs` is generated by FastAPI and always matches the code. The raw schema is at `/openapi.json`.
2. **Postman**: the collection and a `Local` environment are exported to [`docs/postman/`](docs/postman/), and
   the published documentation is linked at the top of this file. Every request has a description and saved
   example responses.
3. **Automated tests**: `pytest` (see above) covers authentication, authorization, validation, per-user isolation,
   the watch-progress rules and the recommendation logic.

### Running the Postman tests

1. Start the API (`uvicorn app.main:app --reload`).
2. In Postman, import both files from `docs/postman/` and select the **Local** environment (top-right dropdown).
3. Right-click the **Test Flow** folder and choose **Run folder**, then **Run**.

The **Test Flow** folder runs a complete scenario in order: register (with a fresh random email each run), login
(the token is stored in the environment automatically), list anime, get one anime, add to watchlist, get the
watchlist, set progress, log a watched anime, and get recommendations. Each request has test scripts that check the
status code and the shape of the response.

![Postman Collection Runner result 1](docs/image/postman-run-1.png)
![Postman Collection Runner result 2](docs/image/postman-run-2.png)

To run the same collection against the deployed API, duplicate the **Local** environment, set `baseUrl` to the
deployed URL, and run the folder again.

## Design and technical decisions

### Database (ERD)

```mermaid
erDiagram
    USERS ||--o{ WATCHLISTS : "saves"
    USERS ||--o{ REVIEWS : "writes"
    USERS ||--o{ WATCH_PROGRESS : "tracks"
    ANIMES ||--o{ WATCHLISTS : "appears in"
    ANIMES ||--o{ REVIEWS : "is reviewed in"
    ANIMES ||--o{ WATCH_PROGRESS : "is followed in"
    ANIMES }o--o{ GENRES : "anime_genres"

    USERS {
        int id PK
        string username
        string email UK
        string password_hash
        datetime created_at
    }
    ANIMES {
        int id PK
        string title
        int year
        string studio
        float rating
        string episodes
        int total_episodes
        text synopsis
        text poster_url
        json cast_members
    }
    GENRES {
        int id PK
        string name UK
    }
    WATCHLISTS {
        int id PK
        int user_id FK
        int anime_id FK
        datetime created_at
    }
    REVIEWS {
        int id PK
        int user_id FK
        int anime_id FK
        int rating
        text review
        datetime created_at
    }
    WATCH_PROGRESS {
        int id PK
        int user_id FK
        int anime_id FK
        string status
        int current_episode
        datetime updated_at
    }
```

- `watchlists`, `reviews` and `watch_progress` each have a **unique constraint on `(user_id, anime_id)`**. Duplicates
  are rejected by the database itself (so the rule holds even under concurrent requests) and translated into HTTP 409.
- `reviews.rating` is protected by `CHECK (rating BETWEEN 1 AND 5)`, and `watch_progress` by
  `CHECK (current_episode >= 0)` and a check on the allowed `status` values, in addition to Pydantic validation.
- Genres are normalised into their own table (many-to-many) so genre filtering is a real query; the cast list is a
  JSON column because it is only displayed, never searched.
- `animes.episodes` is display text (for example `"24 episodes"` or `"1 film (125 menit)"`), while
  `animes.total_episodes` is the number used for validation. A film counts as 1 episode.
- All foreign keys use `ON DELETE CASCADE`.
- `username` is a display name and is intentionally **not** unique; the unique identity for login is the email.
- Seeding inserts explicit anime ids; on PostgreSQL the seeder also re-syncs the id sequence so later inserts cannot collide.

### Security

- Passwords are hashed with **bcrypt** (a unique salt per password) and are never returned in any response.
- JWTs use HS256 with an `exp` claim. When decoding, the accepted algorithm is whitelisted, so tokens with
  `alg: none` or any other algorithm are rejected.
- `user_id` is always taken from the verified **token**, never from the request body or URL, so users cannot
  read or modify each other's data. Another user's entry answers 404 (not 403) so its existence is not revealed.
- Login returns the same error for "unknown email" and "wrong password", and runs a dummy bcrypt check for unknown
  emails so response times do not reveal which emails are registered.
- Input is validated with Pydantic (type, length, range). SQL goes through the ORM (parameterised queries), and
  `LIKE` wildcards in the search box are escaped.
- Unexpected errors are logged on the server only; clients receive a generic message.
- **Supabase:** Row Level Security is enabled on all tables. The backend connects as the database owner role, which
  bypasses RLS, while Supabase's auto-generated REST API is blocked from reading or writing the tables directly.

### Watch progress

`PUT /api/progress/{animeId}` creates the entry or updates it, so a client never has to know whether one exists.

- `status` must be one of `watching`, `completed`, `on_hold`, `dropped`.
- `currentEpisode` cannot be negative or exceed the anime's `total_episodes` (answered with 400).
- Setting the status to `completed` moves the counter to the last episode automatically.
- `GET /api/progress` lists the current user's entries, most recently updated first, and can be filtered with `?status=`.

### Recommendations

`GET /api/recommendations` is computed in plain Python from the user's own history, so it is deterministic, needs
no external service and can be unit-tested without a database (`app/services/recommender.py`).

1. **Taste profile.** Anime the user rated **4 or 5** are "liked". Each liked anime adds its genres to the profile,
   weighted by the rating (a 5-star review counts more than a 4-star one). The studios of liked anime are remembered too.
2. **Scoring.** Every anime the user has not seen yet is scored:

   ```text
   score = 0.60 × genre match + 0.15 × same studio + 0.25 × global rating
   ```

   Anime with no genre or studio in common with the profile are skipped.
3. **Exclusions.** Anime that are already reviewed, on the watchlist or in the progress list are never recommended.
4. **Reason.** Each result names the liked anime it resembles most, for example
   `Karena kamu menyukai Steins;Gate (genre sama: Sci-Fi, Drama)`.
5. **Fallback.** Without any liked anime (a new user, or only low ratings) the endpoint returns the highest-rated
   anime instead.

Results are sorted by score, then by rating, then by id, so the same input always gives the same output.
`limit` defaults to 5 and accepts 1–20.

### Known limitations and future work

- **No migration tool.** Tables are created with `create_all`, which never alters existing tables. For schema
  changes in production, adopt Alembic.
- **No rate limiting.** bcrypt makes every password guess slow, but the number of login attempts is not capped.
  A limiter on `/api/auth/login` would be the next hardening step.
- **JWTs cannot be revoked** before they expire. Short-lived access tokens plus refresh tokens would fix that.
- **Watchlist, watched log and progress are independent.** Logging an anime as watched does not remove it from the
  watchlist or the progress list.
- **One review per user and anime.** A second submission answers 409; an update endpoint could be added.
- Recommendations are content-based. With very few users, collaborative filtering would add little.

## Deployment (Vercel + Supabase)

The API is deployed on **Vercel**, which runs FastAPI natively as a
serverless function, and uses **Supabase** for PostgreSQL.

### 1. Prepare the database

1. Create a Supabase project and copy a **pooler** connection string (**Connect → Connection pooling**).
   For Vercel use the **Transaction pooler** (port `6543`): serverless functions open many short-lived connections.
   The app detects `pooler.supabase.com` and disables prepared statements automatically, which that mode requires.
2. Create the tables and seed the anime **once, from your machine** (the seeder is not run on Vercel):

   ```bash
   cd backend
   # put the Supabase URL in .env as DATABASE_URL, then:
   python -m app.seed
   ```

3. Enable Row Level Security so the tables cannot be accessed through Supabase's REST API.
   Run this in the Supabase **SQL Editor**:

   ```sql
   ALTER TABLE public.users          ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.animes         ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.genres         ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.anime_genres   ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.watchlists     ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.reviews        ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.watch_progress ENABLE ROW LEVEL SECURITY;
   ```

   The backend is unaffected because it connects as the `postgres` role, which bypasses RLS.
   (If you ever drop and recreate the tables, run this again.)

### 2. Create the Vercel project

1. In Vercel choose **Add New → Project** and import this GitHub repository.
2. Configure the project:

   | Setting | Value |
   |---|---|
   | Framework Preset | `FastAPI` (auto-detected; `Other` also works) |
   | **Root Directory** | **`backend`** |
   | Build and Output Settings | Leave everything at the defaults. Python projects need no build command or output directory, and Vercel installs `requirements.txt` automatically. |

3. Add the **Environment Variables** (values without quotes), then click **Deploy**:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | Supabase Transaction pooler URL (port 6543) |
   | `JWT_SECRET` | A newly generated secret (see the table above) |

   Mark the secrets as **Sensitive** if Vercel offers the option. Environment variables only apply to **new**
   deployments, so after changing one, trigger **Redeploy** from the Deployments tab.

### 3. Verify the deployment

Use your **production domain** (`https://<project>.vercel.app`), not the long per-deployment URLs:

```bash
curl https://<project>.vercel.app/api/health         # {"status":"ok"}
curl https://<project>.vercel.app/api/anime          # the 20 seeded anime
```

Then open `/docs`, log in via `POST /api/auth/login`, click **Authorize**, and try the protected endpoints.
You can also run the Postman **Test Flow** against the deployed URL (see above).

### Notes and troubleshooting

- **Deployment Protection.** On the Hobby plan the production domain is public, while preview and per-deployment URLs
  can require a Vercel login. If a request returns a Vercel login page instead of JSON, you are on a protected URL.
- **Cold starts.** Serverless functions start on demand, so the first request after a quiet period is slower.
- **Entrypoint not found.** If Vercel cannot locate the app, add `backend/index.py` containing
  `from app.main import app  # noqa: F401`.
- **Dependency build errors.** Pin the Python version by adding `backend/.python-version` (for example `3.12`).
- **Database connection errors.** Make sure you use the pooler host (`...pooler.supabase.com`), that the password
  has no unescaped special characters (`@` becomes `%40`), and that the Supabase project is not paused.
- **Missing column or table after an update.** `create_all` does not alter existing tables. Drop the old tables
  and run `python -m app.seed` again.