from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Actor, Movie, MovieActor, MovieGenre, Genre
from app.schemas import (
    AverageRatingSummary,
    GenreDistributionItem,
    MovieRead,
    MoviesByYearItem,
    TopActorItem,
)


router = APIRouter(prefix="/analytics", tags=["analytics"])

DEFAULT_LIMIT = 10
MAX_LIMIT = 100


@router.get("/top-rated", response_model=list[MovieRead])
def top_rated_movies(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    min_votes: int = Query(default=100, ge=0),
    db: Session = Depends(get_db),
) -> list[Movie]:
    return (
        db.query(Movie)
        .filter(Movie.rating.is_not(None), Movie.vote_count >= min_votes)
        .order_by(Movie.rating.desc(), Movie.vote_count.desc(), Movie.id.asc())
        .limit(limit)
        .all()
    )


@router.get("/most-popular", response_model=list[MovieRead])
def most_popular_movies(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    db: Session = Depends(get_db),
) -> list[Movie]:
    return (
        db.query(Movie)
        .order_by(Movie.vote_count.desc(), Movie.rating.desc(), Movie.id.asc())
        .limit(limit)
        .all()
    )


@router.get("/genre-distribution", response_model=list[GenreDistributionItem])
def genre_distribution(db: Session = Depends(get_db)) -> list[GenreDistributionItem]:
    rows = (
        db.query(
            Genre.id.label("genre_id"),
            Genre.name.label("genre_name"),
            func.count(MovieGenre.movie_id).label("movie_count"),
        )
        .join(MovieGenre, MovieGenre.genre_id == Genre.id)
        .group_by(Genre.id, Genre.name)
        .order_by(func.count(MovieGenre.movie_id).desc(), Genre.name.asc())
        .all()
    )

    return [
        GenreDistributionItem(
            genre_id=row.genre_id,
            genre_name=row.genre_name,
            movie_count=row.movie_count,
        )
        for row in rows
    ]


@router.get("/top-actors", response_model=list[TopActorItem])
def top_actors(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    db: Session = Depends(get_db),
) -> list[TopActorItem]:
    rows = (
        db.query(
            Actor.id.label("actor_id"),
            Actor.name.label("actor_name"),
            func.count(MovieActor.movie_id).label("movie_count"),
        )
        .join(MovieActor, MovieActor.actor_id == Actor.id)
        .group_by(Actor.id, Actor.name)
        .order_by(func.count(MovieActor.movie_id).desc(), Actor.name.asc())
        .limit(limit)
        .all()
    )

    return [
        TopActorItem(
            actor_id=row.actor_id,
            actor_name=row.actor_name,
            movie_count=row.movie_count,
        )
        for row in rows
    ]


@router.get("/actor/{actor_id}/movies", response_model=list[MovieRead])
def movies_for_actor(actor_id: int, db: Session = Depends(get_db)) -> list[Movie]:
    actor_exists = db.query(Actor.id).filter(Actor.id == actor_id).first()
    if actor_exists is None:
        raise HTTPException(status_code=404, detail="Actor not found.")

    return (
        db.query(Movie)
        .join(MovieActor, MovieActor.movie_id == Movie.id)
        .filter(MovieActor.actor_id == actor_id)
        .order_by(Movie.rating.desc(), Movie.vote_count.desc(), Movie.id.asc())
        .all()
    )


@router.get("/movies-by-year", response_model=list[MoviesByYearItem])
def movies_by_year(db: Session = Depends(get_db)) -> list[MoviesByYearItem]:
    rows = (
        db.query(
            Movie.release_year.label("release_year"),
            func.count(Movie.id).label("movie_count"),
        )
        .filter(Movie.release_year.is_not(None))
        .group_by(Movie.release_year)
        .order_by(Movie.release_year.asc())
        .all()
    )

    return [
        MoviesByYearItem(release_year=row.release_year, movie_count=row.movie_count)
        for row in rows
    ]


@router.get("/average-rating", response_model=AverageRatingSummary)
def average_rating(
    min_votes: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> AverageRatingSummary:
    avg_rating, total_movies = (
        db.query(func.avg(Movie.rating), func.count(Movie.id))
        .filter(Movie.rating.is_not(None), Movie.vote_count >= min_votes)
        .one()
    )

    return AverageRatingSummary(
        average_rating=float(avg_rating) if avg_rating is not None else None,
        total_movies=total_movies,
        min_votes=min_votes,
    )
