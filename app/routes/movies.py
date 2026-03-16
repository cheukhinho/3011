from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Movie
from app.schemas import MovieCreate, MovieRead, MovieUpdate


router = APIRouter(prefix="/movies", tags=["movies"])


@router.post("", response_model=MovieRead, status_code=status.HTTP_201_CREATED)
def create_movie(payload: MovieCreate, db: Session = Depends(get_db)) -> Movie:
    movie = Movie(**payload.model_dump())
    db.add(movie)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Movie already exists.") from exc

    db.refresh(movie)
    return movie


@router.get("", response_model=list[MovieRead])
def get_movies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[Movie]:
    return db.query(Movie).order_by(Movie.id).offset(skip).limit(limit).all()


@router.get("/{movie_id}", response_model=MovieRead)
def get_movie(movie_id: int, db: Session = Depends(get_db)) -> Movie:
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found.")
    return movie


@router.put("/{movie_id}", response_model=MovieRead)
def update_movie(movie_id: int, payload: MovieUpdate, db: Session = Depends(get_db)) -> Movie:
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found.")

    for field_name, field_value in payload.model_dump(exclude_unset=True).items():
        setattr(movie, field_name, field_value)

    db.commit()
    db.refresh(movie)
    return movie


@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movie(movie_id: int, db: Session = Depends(get_db)) -> None:
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found.")

    db.delete(movie)
    db.commit()
