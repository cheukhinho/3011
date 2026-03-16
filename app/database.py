import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


def _resolve_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    allow_sqlite = os.getenv("ALLOW_SQLITE_URLS") == "1"

    if not database_url:
        if allow_sqlite:
            return "sqlite:///./movies.db"

        raise RuntimeError(
            "DATABASE_URL must be set to a PostgreSQL connection string. "
            "Set ALLOW_SQLITE_URLS=1 only for local SQLite smoke tests."
        )

    if database_url.startswith("sqlite") and not allow_sqlite:
        raise RuntimeError(
            "SQLite is only supported when ALLOW_SQLITE_URLS=1. "
            "Use PostgreSQL for the application database."
        )

    return database_url


DATABASE_URL = _resolve_database_url()

engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base = declarative_base()


ANALYTICS_INDEX_DDL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_movies_tmdb_id ON movies (tmdb_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_genres_tmdb_id ON genres (tmdb_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_actors_tmdb_id ON actors (tmdb_id)",
    "CREATE INDEX IF NOT EXISTS ix_genres_name ON genres (name)",
    "CREATE INDEX IF NOT EXISTS ix_movies_rating_vote_count ON movies (rating, vote_count)",
    "CREATE INDEX IF NOT EXISTS ix_movies_release_year ON movies (release_year)",
    "CREATE INDEX IF NOT EXISTS ix_actors_name ON actors (name)",
    "CREATE INDEX IF NOT EXISTS ix_movie_genres_genre_id_movie_id ON movie_genres (genre_id, movie_id)",
    "CREATE INDEX IF NOT EXISTS ix_movie_actors_actor_id ON movie_actors (actor_id)",
    "CREATE INDEX IF NOT EXISTS ix_reviews_movie_id ON reviews (movie_id)",
)


def ensure_schema_extensions() -> None:
    """Backfill missing columns for older local databases without requiring migrations."""
    inspector = inspect(engine)
    missing_columns = {
        "movies": {"tmdb_id"},
        "genres": {"tmdb_id"},
        "actors": {"tmdb_id"},
    }

    with engine.begin() as connection:
        for table_name, required_columns in missing_columns.items():
            if table_name not in inspector.get_table_names():
                continue

            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name in sorted(required_columns - existing_columns):
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} INTEGER"))


def ensure_analytics_indexes() -> None:
    """Create import and analytics indexes even when tables already existed before code changes."""
    with engine.begin() as connection:
        for ddl in ANALYTICS_INDEX_DDL:
            connection.execute(text(ddl))