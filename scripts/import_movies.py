import json
import argparse
import os
import sys

import pandas as pd
from sqlalchemy import select

# allow script to access the app folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base, SessionLocal, engine, ensure_analytics_indexes, ensure_schema_extensions
from app.models import Actor, Genre, Movie, MovieActor, MovieGenre


TOP_CAST_LIMIT = 5


def _parse_json_list(value) -> list[dict]:
    if pd.isna(value) or value in ("", "[]", None):
        return []

    return json.loads(value)


def _parse_optional_int(value):
    if pd.isna(value) or value == "":
        return None

    return int(value)


def _parse_optional_year(value):
    if pd.isna(value) or not value:
        return None

    return int(str(value)[:4])


def _build_credit_lookup(credits_df: pd.DataFrame) -> dict[int, list[dict]]:
    credits_df = credits_df.copy()
    credits_df["movie_id"] = credits_df["movie_id"].astype(int)
    return {
        int(row.movie_id): _parse_json_list(row.cast)
        for row in credits_df.itertuples(index=False)
    }

def import_movies(movies_csv_path: str, credits_csv_path: str) -> None:
    # load datasets
    movies_df = pd.read_csv(movies_csv_path)
    credits_df = pd.read_csv(credits_csv_path)
    credits_lookup = _build_credit_lookup(credits_df)

    # ensure schema exists before inserting data
    Base.metadata.create_all(bind=engine)
    ensure_schema_extensions()
    ensure_analytics_indexes()

    with SessionLocal() as db:
        try:
            movie_cache = {movie.tmdb_id: movie for movie in db.scalars(select(Movie).where(Movie.tmdb_id.is_not(None))).all()}
            genre_cache = {genre.tmdb_id: genre for genre in db.scalars(select(Genre).where(Genre.tmdb_id.is_not(None))).all()}
            actor_cache = {actor.tmdb_id: actor for actor in db.scalars(select(Actor).where(Actor.tmdb_id.is_not(None))).all()}

            legacy_genres_by_name = {
                genre.name: genre for genre in db.scalars(select(Genre).where(Genre.tmdb_id.is_(None))).all()
            }
            legacy_actors_by_name = {
                actor.name: actor for actor in db.scalars(select(Actor).where(Actor.tmdb_id.is_(None))).all()
            }

            for movie_row in movies_df.itertuples(index=False):
                tmdb_movie_id = int(movie_row.id)
                movie = movie_cache.get(tmdb_movie_id)

                if movie is None:
                    movie = db.scalar(
                        select(Movie).where(
                            Movie.tmdb_id.is_(None),
                            Movie.title == movie_row.title,
                            Movie.release_year == _parse_optional_year(movie_row.release_date),
                        )
                    )

                if movie is None:
                    movie = Movie(tmdb_id=tmdb_movie_id)
                    db.add(movie)

                movie.tmdb_id = tmdb_movie_id
                movie.title = movie_row.title
                movie.description = movie_row.overview
                movie.release_year = _parse_optional_year(movie_row.release_date)
                movie.runtime = _parse_optional_int(movie_row.runtime)
                movie.rating = movie_row.vote_average if pd.notna(movie_row.vote_average) else None
                movie.vote_count = _parse_optional_int(movie_row.vote_count)
                movie_cache[tmdb_movie_id] = movie

                movie.genres.clear()
                seen_genre_ids = set()
                for genre_data in _parse_json_list(movie_row.genres):
                    tmdb_genre_id = int(genre_data["id"])
                    genre = genre_cache.get(tmdb_genre_id)

                    if genre is None:
                        genre = legacy_genres_by_name.pop(genre_data["name"], None)

                    if genre is None:
                        genre = Genre(tmdb_id=tmdb_genre_id, name=genre_data["name"])
                        db.add(genre)
                        db.flush()
                    else:
                        genre.tmdb_id = tmdb_genre_id
                        genre.name = genre_data["name"]

                    genre_cache[tmdb_genre_id] = genre
                    if genre.id not in seen_genre_ids:
                        seen_genre_ids.add(genre.id)
                        movie.genres.append(MovieGenre(genre=genre))

                movie.actors.clear()
                seen_actor_ids = set()
                for actor_data in credits_lookup.get(tmdb_movie_id, [])[:TOP_CAST_LIMIT]:
                    tmdb_actor_id = int(actor_data["id"])
                    actor = actor_cache.get(tmdb_actor_id)

                    if actor is None:
                        actor = legacy_actors_by_name.pop(actor_data["name"], None)

                    if actor is None:
                        actor = Actor(tmdb_id=tmdb_actor_id, name=actor_data["name"])
                        db.add(actor)
                        db.flush()
                    else:
                        actor.tmdb_id = tmdb_actor_id
                        actor.name = actor_data["name"]

                    actor_cache[tmdb_actor_id] = actor
                    if actor.id not in seen_actor_ids:
                        seen_actor_ids.add(actor.id)
                        movie.actors.append(MovieActor(actor=actor))

            db.commit()
        except Exception:
            db.rollback()
            raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import TMDB movies and credits CSV files into the database.")
    parser.add_argument("--movies-csv", default="data/tmdb_5000_movies.csv", help="Path to movies CSV file")
    parser.add_argument("--credits-csv", default="data/tmdb_5000_credits.csv", help="Path to credits CSV file")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    import_movies(args.movies_csv, args.credits_csv)
    print("Dataset successfully imported!")