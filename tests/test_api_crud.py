import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# Ensure app imports can resolve a local SQLite URL in test runs.
os.environ.setdefault("ALLOW_SQLITE_URLS", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/api_test_bootstrap.db")

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "api_test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

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


def _create_movie(client: TestClient, title: str, tmdb_id: int | None = None):
    payload = {
        "title": title,
        "description": f"{title} description",
        "release_year": 2024,
        "runtime": 120,
        "rating": 7.5,
        "vote_count": 100,
    }
    if tmdb_id is not None:
        payload["tmdb_id"] = tmdb_id

    return client.post("/movies", json=payload)


def test_movies_crud_and_limits(client: TestClient) -> None:
    created = [_create_movie(client, f"Movie {idx}", tmdb_id=1000 + idx) for idx in range(3)]
    assert all(response.status_code == 201 for response in created)

    list_response = client.get("/movies", params={"limit": 2, "skip": 0})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2

    movie_id = created[0].json()["id"]
    get_response = client.get(f"/movies/{movie_id}")
    assert get_response.status_code == 200

    update_response = client.put(f"/movies/{movie_id}", json={"title": "Movie 0 Updated"})
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Movie 0 Updated"

    delete_response = client.delete(f"/movies/{movie_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/movies/{movie_id}")
    assert missing_response.status_code == 404


def test_actor_edges_and_limits(client: TestClient) -> None:
    actor_a = client.post("/actors", json={"name": "Actor A", "tmdb_id": 2001, "birth_year": 1980})
    actor_b = client.post("/actors", json={"name": "Actor B", "tmdb_id": 2002, "birth_year": 1982})
    assert actor_a.status_code == 201
    assert actor_b.status_code == 201

    duplicate_actor = client.post("/actors", json={"name": "Actor Dup", "tmdb_id": 2002})
    assert duplicate_actor.status_code == 409

    limited_list = client.get("/actors", params={"limit": 1})
    assert limited_list.status_code == 200
    assert len(limited_list.json()) == 1

    missing_update = client.put("/actors/99999", json={"name": "Ghost Actor"})
    assert missing_update.status_code == 404


def test_reviews_filters_limits_and_edges(client: TestClient) -> None:
    movie_response = _create_movie(client, "Review Target", tmdb_id=3001)
    assert movie_response.status_code == 201
    movie_id = movie_response.json()["id"]

    first_review = client.post(
        "/reviews",
        json={"movie_id": movie_id, "user_name": "alice", "rating": 9, "comment": "Great"},
    )
    second_review = client.post(
        "/reviews",
        json={"movie_id": movie_id, "user_name": "bob", "rating": 8, "comment": "Nice"},
    )
    assert first_review.status_code == 201
    assert second_review.status_code == 201

    missing_movie_review = client.post(
        "/reviews",
        json={"movie_id": 99999, "user_name": "ghost", "rating": 7, "comment": "No movie"},
    )
    assert missing_movie_review.status_code == 404

    filtered = client.get("/reviews", params={"movie_id": movie_id, "limit": 1})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    invalid_limit = client.get("/reviews", params={"limit": 0})
    assert invalid_limit.status_code == 422

    invalid_rating = client.post(
        "/reviews",
        json={"movie_id": movie_id, "user_name": "bad", "rating": 11, "comment": "Too high"},
    )
    assert invalid_rating.status_code == 422

    review_id = first_review.json()["id"]
    assert client.delete(f"/reviews/{review_id}").status_code == 204
    assert client.delete(f"/reviews/{review_id}").status_code == 404


def test_pagination_validation_edges(client: TestClient) -> None:
    assert client.get("/movies", params={"limit": 500}).status_code == 422
    assert client.get("/movies", params={"skip": -1}).status_code == 422
    assert client.get("/actors", params={"skip": -1}).status_code == 422
    assert client.get("/reviews", params={"limit": 300}).status_code == 422
