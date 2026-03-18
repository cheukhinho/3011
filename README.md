# Movie Analytics API

## Project Overview

Movie Analytics API is a FastAPI backend built on top of the TMDB 5000 dataset.
It supports:

- Dataset import into a relational database
- CRUD endpoints for movies, actors, and reviews
- Analytics endpoints (top rated, most popular, genre distribution, actor analytics, trends)
- Basic recommendations based on shared genres and similar ratings

Tech stack:

- Backend: FastAPI
- ORM: SQLAlchemy
- Database: PostgreSQL (primary), SQLite (local/testing only)
- Testing: pytest
- API Docs: Swagger UI (FastAPI)

Dataset source:
https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata

## Setup Instructions

### 1. Clone and enter project

```bash
git clone <your-repo-url>
cd 3011
```

### 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure database environment

For production-like usage, use PostgreSQL:

```bash
export DATABASE_URL="postgresql+psycopg2://<user>:<password>@<host>:<port>/<database>"
```

For local SQLite smoke testing only:

```bash
export ALLOW_SQLITE_URLS=1
export DATABASE_URL="sqlite:///./movies.db"
```

### 5. Import TMDB dataset

```bash
python scripts/import_movies.py
```

This reads:

- data/tmdb_5000_movies.csv
- data/tmdb_5000_credits.csv

You can override paths:

```bash
python scripts/import_movies.py --movies-csv <path-to-movies-csv> --credits-csv <path-to-credits-csv>
```

## How To Run The API

Start the FastAPI server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Documentation

- API Documentation (PDF): docs/api_documentation.pdf
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Technical Report: docs/technical_report.pdf
- Presentation Slides: docs/presentation.pptx

Example endpoints:

- CRUD: /movies, /actors, /reviews
- Analytics: /analytics/top-rated, /analytics/most-popular, /analytics/genre-distribution
- Recommendations: /recommendations/{movie_id}