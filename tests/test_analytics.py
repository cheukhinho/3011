import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

os.environ.setdefault("ALLOW_SQLITE_URLS", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/analytics_test_bootstrap.db")

from app.database import Base, get_db
from app.main import app
from app.models import Actor, Genre, Movie, MovieActor, MovieGenre


@pytest.fixture()
def client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as session:
        action = Genre(tmdb_id=1, name="Action")
        drama = Genre(tmdb_id=2, name="Drama")

        movie_a = Movie(tmdb_id=1001, title="A", rating=9.0, vote_count=1000, release_year=2020)
        movie_b = Movie(tmdb_id=1002, title="B", rating=8.5, vote_count=900, release_year=2021)
        movie_c = Movie(tmdb_id=1003, title="C", rating=7.0, vote_count=200, release_year=2020)
        movie_d = Movie(tmdb_id=1004, title="D", rating=8.0, vote_count=800, release_year=2021)

        actor_1 = Actor(tmdb_id=501, name="Actor One")
        actor_2 = Actor(tmdb_id=502, name="Actor Two")

        session.add_all([action, drama, movie_a, movie_b, movie_c, movie_d, actor_1, actor_2])
        session.flush()

        session.add_all(
            [
                MovieGenre(movie_id=movie_a.id, genre_id=action.id),
                MovieGenre(movie_id=movie_b.id, genre_id=action.id),
                MovieGenre(movie_id=movie_c.id, genre_id=drama.id),
                MovieGenre(movie_id=movie_d.id, genre_id=action.id),
                MovieGenre(movie_id=movie_d.id, genre_id=drama.id),
            ]
        )

        session.add_all(
            [
                MovieActor(movie_id=movie_a.id, actor_id=actor_1.id),
                MovieActor(movie_id=movie_b.id, actor_id=actor_1.id),
                MovieActor(movie_id=movie_d.id, actor_id=actor_1.id),
                MovieActor(movie_id=movie_c.id, actor_id=actor_2.id),
                MovieActor(movie_id=movie_d.id, actor_id=actor_2.id),
            ]
        )

        session.commit()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()


def test_movie_analytics_endpoints(client: TestClient) -> None:
    top_rated = client.get("/analytics/top-rated", params={"limit": 2, "min_votes": 500})
    assert top_rated.status_code == 200
    top_rated_json = top_rated.json()
    assert [movie["title"] for movie in top_rated_json] == ["A", "B"]

    most_popular = client.get("/analytics/most-popular", params={"limit": 2})
    assert most_popular.status_code == 200
    assert [movie["title"] for movie in most_popular.json()] == ["A", "B"]

    distribution = client.get("/analytics/genre-distribution")
    assert distribution.status_code == 200
    distribution_json = distribution.json()
    assert distribution_json[0]["genre_name"] == "Action"
    assert distribution_json[0]["movie_count"] == 3


def test_actor_analytics_endpoints(client: TestClient) -> None:
    top_actors = client.get("/analytics/top-actors", params={"limit": 2})
    assert top_actors.status_code == 200
    top_actors_json = top_actors.json()
    assert top_actors_json[0]["actor_name"] == "Actor One"
    assert top_actors_json[0]["movie_count"] == 3

    actor_id = top_actors_json[0]["actor_id"]
    actor_movies = client.get(f"/analytics/actor/{actor_id}/movies")
    assert actor_movies.status_code == 200
    assert len(actor_movies.json()) == 3

    missing_actor = client.get("/analytics/actor/99999/movies")
    assert missing_actor.status_code == 404


def test_trends_and_recommendations(client: TestClient) -> None:
    by_year = client.get("/analytics/movies-by-year")
    assert by_year.status_code == 200
    assert by_year.json() == [
        {"release_year": 2020, "movie_count": 2},
        {"release_year": 2021, "movie_count": 2},
    ]

    avg_rating = client.get("/analytics/average-rating", params={"min_votes": 0})
    assert avg_rating.status_code == 200
    avg_json = avg_rating.json()
    assert avg_json["total_movies"] == 4
    assert avg_json["average_rating"] == pytest.approx(8.125, rel=1e-4)

    top_rated = client.get("/analytics/top-rated", params={"limit": 1})
    target_movie_id = top_rated.json()[0]["id"]
    recommendations = client.get(f"/recommendations/{target_movie_id}", params={"limit": 3})
    assert recommendations.status_code == 200
    recommendation_titles = [movie["title"] for movie in recommendations.json()]
    assert recommendation_titles[:2] == ["B", "D"]

    assert client.get("/recommendations/99999").status_code == 404


def test_analytics_pagination_validation_edges(client: TestClient) -> None:
    assert client.get("/analytics/top-rated", params={"limit": 0}).status_code == 422
    assert client.get("/analytics/most-popular", params={"limit": 101}).status_code == 422
    assert client.get("/analytics/top-actors", params={"limit": 0}).status_code == 422
    assert client.get("/analytics/average-rating", params={"min_votes": -1}).status_code == 422
    assert client.get("/recommendations/1", params={"limit": 0}).status_code == 422
