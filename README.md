# AgroVibe AZ

AI-powered media automation platform for agricultural producers in Azerbaijan.

Farmers upload raw rural videos via a PWA. The backend processes them through
an AI pipeline — stabilization, audio enhancement, LLM metadata generation —
then auto-posts the result to Instagram and pins it on an interactive GPS map.

---

## Tech Stack

| Layer              | Technology                                          |
| ------------------ | --------------------------------------------------- |
| Runtime            | Python 3.11+                                        |
| Framework          | FastAPI                                             |
| Server             | Uvicorn                                             |
| Database           | SQLite + SQLAlchemy (async) + Alembic               |
| Auth               | JWT (access + refresh tokens), Google OAuth2        |
| AI / LLM           | OpenAI GPT-4o                                       |
| Social Publish     | Meta Graph API (Instagram Reels)                    |
| Logging            | structlog (structured JSON)                         |
| Testing            | pytest, pytest-asyncio, httpx                       |

---

## Quickstart

```bash
# 1. Clone and enter the project
cd agrovibe-backend

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill in your environment variables
cp .env.example .env

# 5. Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`.

---

## Environment Variables

| Variable                  | Description                          |
| ------------------------- | ------------------------------------ |
| `DATABASE_URL`            | SQLite async connection string       |
| `SECRET_KEY`              | JWT signing secret                   |
| `OPENAI_API_KEY`          | OpenAI API key for GPT-4o            |
| `META_ACCESS_TOKEN`       | Meta Graph API access token          |
| `META_INSTAGRAM_ID`       | Instagram Business Account ID        |
| `GOOGLE_CLIENT_ID`        | Google OAuth2 client ID              |
| `GOOGLE_CLIENT_SECRET`    | Google OAuth2 client secret          |

---

## API Endpoints

| Method | Path                              | Description                    |
| ------ | --------------------------------- | ------------------------------ |
| GET    | `/health`                         | Health check                   |
| POST   | `/api/v1/auth/register`           | Register a new farmer          |
| POST   | `/api/v1/auth/login`              | Login                          |
| POST   | `/api/v1/auth/refresh`            | Refresh access token           |
| POST   | `/api/v1/auth/google`             | Google OAuth2 login            |
| GET    | `/api/v1/farmers/me`              | Get current farmer profile     |
| PATCH  | `/api/v1/farmers/me`              | Update farmer profile          |
| GET    | `/api/v1/farmers/{id}`            | Get any farmer profile         |
| POST   | `/api/v1/videos/upload`           | Upload raw video               |
| GET    | `/api/v1/videos/{id}`             | Get video status / detail      |
| GET    | `/api/v1/videos`                  | List current farmer's videos   |
| GET    | `/api/v1/map/geojson`             | GeoJSON of published videos    |
| GET    | `/static/media/processed/{file}`  | Serve processed video files    |

---

## Pipeline Flow

```
                       AgroVibe Pipeline
    ┌─────────────────────────────────────────────────────┐
    │                                                     │
    │   ┌──────────┐    ┌──────────────┐                  │
    │   │  Farmer   │    │   Upload     │                  │
    │   │  (PWA)    │───►│  /api/v1/    │                  │
    │   │           │    │  videos/     │                  │
    │   └──────────┘    │  upload      │                  │
    │                   └──────┬───────┘                  │
    │                          │                          │
    │                   ┌──────▼───────┐                  │
    │                   │   PENDING    │                  │
    │                   │  (saved to   │                  │
    │                   │   media/raw) │                  │
    │                   └──────┬───────┘                  │
    │                          │                          │
    │               asyncio.create_task()                 │
    │                          │                          │
    │                   ┌──────▼───────┐                  │
    │                   │ STABILIZING  │  External API    │
    │                   │              │─────────────────►│
    │                   └──────┬───────┘                  │
    │                          │                          │
    │                   ┌──────▼──────────┐               │
    │                   │ AUDIO_PROCESSING│  External API  │
    │                   │                 │──────────────►│
    │                   └──────┬──────────┘               │
    │                          │                          │
    │                   ┌──────▼──────────┐               │
    │                   │GENERATING_      │  OpenAI       │
    │                   │METADATA         │  GPT-4o       │
    │                   │(AZ / EN / AR)   │──────────────►│
    │                   └──────┬──────────┘               │
    │                          │                          │
    │                   ┌──────▼───────┐                  │
    │                   │  PUBLISHING  │  Meta Graph API  │
    │                   │              │─────────────────►│
    │                   └──────┬───────┘                  │
    │                          │                          │
    │                   ┌──────▼───────┐                  │
    │                   │  PUBLISHED   │                  │
    │                   │ (media/      │                  │
    │                   │  processed)  │                  │
    │                   └──────────────┘                  │
    │                                                     │
    │   On any error: ───► FAILED (error_message set)     │
    │                                                     │
    └─────────────────────────────────────────────────────┘
```

---

## Project Structure

```
app/
├── main.py                  # FastAPI app factory
├── config.py                # pydantic-settings
├── dependencies.py          # Shared DI (DB session, current user)
├── api/v1/                  # Route handlers
├── core/                    # Security, exceptions, logging
├── models/                  # SQLAlchemy models
├── schemas/                 # Pydantic schemas
├── services/                # Business logic
├── pipeline/                # AI processing pipeline
├── db/                      # Engine, session, init
└── utils/                   # GPS helpers, file validation
media/
├── raw/                     # Uploaded originals
└── processed/               # Processed outputs (served via /static/media)
tests/                       # pytest test suite
```

---

## Running Tests

```bash
pytest -v --asyncio-mode=auto
```

---

## License

Proprietary — All rights reserved.
