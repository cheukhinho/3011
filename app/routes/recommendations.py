from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Movie, MovieGenre
from app.schemas import MovieRead


router = APIRouter(prefix="/recommendations", tags=["recommendations"])

DEFAULT_LIMIT = 10
MAX_LIMIT = 50


@router.get("/{movie_id}", response_model=list[MovieRead])
def recommend_movies(
    movie_id: int,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    db: Session = Depends(get_db),
) -> list[Movie]:
    target = db.query(Movie).filter(Movie.id == movie_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Movie not found.")

    target_genre_ids = [
        genre_id for (genre_id,) in db.query(MovieGenre.genre_id).filter(MovieGenre.movie_id == movie_id).all()
    ]

    if target.rating is not None:
        rating_gap = func.abs(func.coalesce(Movie.rating, 0.0) - float(target.rating))
    else:
        rating_gap = func.abs(func.coalesce(Movie.rating, 0.0) - 5.0)

    if target_genre_ids:
        shared_genres = func.sum(
            case(
                (MovieGenre.genre_id.in_(target_genre_ids), 1),
                else_=0,
            )
        )
    else:
        shared_genres = func.sum(0)

    ranked_ids = (
        db.query(Movie.id)
        .outerjoin(MovieGenre, MovieGenre.movie_id == Movie.id)
        .filter(Movie.id != movie_id)
        .group_by(Movie.id)
        .order_by(
            shared_genres.desc(),
            rating_gap.asc(),
            Movie.vote_count.desc(),
            Movie.id.asc(),
        )
        .limit(limit)
        .all()
    )

    ordered_ids = [movie_row.id for movie_row in ranked_ids]
    if not ordered_ids:
        return []

    movies = db.query(Movie).filter(Movie.id.in_(ordered_ids)).all()
    movies_by_id = {movie.id: movie for movie in movies}
    return [movies_by_id[movie_id_value] for movie_id_value in ordered_ids if movie_id_value in movies_by_id]
