from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Movie, Review
from app.schemas import ReviewCreate, ReviewRead


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(payload: ReviewCreate, db: Session = Depends(get_db)) -> Review:
    movie = db.query(Movie).filter(Movie.id == payload.movie_id).first()
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found.")

    review = Review(**payload.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.get("", response_model=list[ReviewRead])
def get_reviews(movie_id: int | None = Query(default=None, ge=1), db: Session = Depends(get_db)) -> list[Review]:
    query = db.query(Review).order_by(Review.id)
    if movie_id is not None:
        query = query.filter(Review.movie_id == movie_id)
    return query.all()


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, db: Session = Depends(get_db)) -> None:
    review = db.query(Review).filter(Review.id == review_id).first()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")

    db.delete(review)
    db.commit()
