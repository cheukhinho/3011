import csv
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture()
def sample_dataset(tmp_path: Path) -> tuple[Path, Path, Path]:
    movies_csv = tmp_path / "movies.csv"
    credits_csv = tmp_path / "credits.csv"
    db_path = tmp_path / "test_movies.db"

    movie_rows = [
        {
            "id": 101,
            "title": "Alpha",
            "genres": json.dumps([{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}]),
            "overview": "Alpha overview",
            "release_date": "2012-05-04",
            "runtime": 120,
            "vote_average": 8.2,
            "vote_count": 1500,
        },
        {
            "id": 202,
            "title": "Alpha",
            "genres": json.dumps([{"id": 18, "name": "Drama"}]),
            "overview": "Second Alpha overview",
            "release_date": "2014-07-18",
            "runtime": 95,
            "vote_average": 7.4,
            "vote_count": 700,
        },
    ]

    with movies_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "title",
                "genres",
                "overview",
                "release_date",
                "runtime",
                "vote_average",
                "vote_count",
            ],
        )
        writer.writeheader()
        writer.writerows(movie_rows)

    credit_rows = [
        {
            "movie_id": 101,
            "title": "Alpha",
            "cast": json.dumps(
                [
                    {"id": 1, "name": "Actor A"},
                    {"id": 1, "name": "Actor A"},
                    {"id": 2, "name": "Actor B"},
                    {"id": 3, "name": "Actor C"},
                    {"id": 4, "name": "Actor D"},
                    {"id": 5, "name": "Actor E"},
                ]
            ),
            "crew": "[]",
        },
        {
            "movie_id": 202,
            "title": "Alpha",
            "cast": json.dumps([{"id": 6, "name": "Actor F"}, {"id": 7, "name": "Actor G"}]),
            "crew": "[]",
        },
    ]

    with credits_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["movie_id", "title", "cast", "crew"])
        writer.writeheader()
        writer.writerows(credit_rows)

    return movies_csv, credits_csv, db_path


def run_importer(repo_root: Path, movies_csv: Path, credits_csv: Path, db_path: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["ALLOW_SQLITE_URLS"] = "1"

    return subprocess.run(
        [
            sys.executable,
            "scripts/import_movies.py",
            "--movies-csv",
            str(movies_csv),
            "--credits-csv",
            str(credits_csv),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def fetch_scalar(db_path: Path, query: str):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(query).fetchone()[0]


def test_imports_movies_genres_actors_and_links(repo_root: Path, sample_dataset: tuple[Path, Path, Path]) -> None:
    movies_csv, credits_csv, db_path = sample_dataset
    result = run_importer(repo_root, movies_csv, credits_csv, db_path)

    assert result.returncode == 0, result.stderr
    assert "Dataset successfully imported!" in result.stdout
    assert fetch_scalar(db_path, "SELECT COUNT(*) FROM movies") == 2
    assert fetch_scalar(db_path, "SELECT COUNT(*) FROM genres") == 3
    assert fetch_scalar(db_path, "SELECT COUNT(*) FROM movie_genres") == 3
    assert fetch_scalar(db_path, "SELECT COUNT(*) FROM actors") == 6
    assert fetch_scalar(db_path, "SELECT COUNT(*) FROM movie_actors") == 6

    assert fetch_scalar(
        db_path,
        "SELECT COUNT(*) FROM movie_genres mg JOIN movies m ON m.id = mg.movie_id WHERE m.tmdb_id = 101",
    ) == 2

    assert fetch_scalar(
        db_path,
        "SELECT COUNT(*) FROM movie_actors ma JOIN movies m ON m.id = ma.movie_id JOIN actors a ON a.id = ma.actor_id WHERE m.tmdb_id = 202 AND a.name = 'Actor F'",
    ) == 1

    assert fetch_scalar(db_path, "SELECT COUNT(*) FROM actors WHERE name = 'Actor E'") == 0


def test_rerun_is_idempotent(repo_root: Path, sample_dataset: tuple[Path, Path, Path]) -> None:
    movies_csv, credits_csv, db_path = sample_dataset

    first = run_importer(repo_root, movies_csv, credits_csv, db_path)
    second = run_importer(repo_root, movies_csv, credits_csv, db_path)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert fetch_scalar(db_path, "SELECT COUNT(*) FROM movies") == 2
    assert fetch_scalar(db_path, "SELECT COUNT(*) FROM genres") == 3
    assert fetch_scalar(db_path, "SELECT COUNT(*) FROM actors") == 6
    assert fetch_scalar(db_path, "SELECT COUNT(*) FROM movie_genres") == 3
    assert fetch_scalar(db_path, "SELECT COUNT(*) FROM movie_actors") == 6
