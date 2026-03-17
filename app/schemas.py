from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MovieBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    release_year: int | None = Field(default=None, ge=1870, le=2100)
    runtime: int | None = Field(default=None, ge=1)
    rating: Decimal | None = Field(default=None, ge=0, le=10)
    vote_count: int | None = Field(default=None, ge=0)


class MovieCreate(MovieBase):
    tmdb_id: int | None = Field(default=None, ge=1)


class MovieUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    release_year: int | None = Field(default=None, ge=1870, le=2100)
    runtime: int | None = Field(default=None, ge=1)
    rating: Decimal | None = Field(default=None, ge=0, le=10)
    vote_count: int | None = Field(default=None, ge=0)


class MovieRead(MovieBase):
    id: int
    tmdb_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActorBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    birth_year: int | None = Field(default=None, ge=1800, le=2100)


class ActorCreate(ActorBase):
    tmdb_id: int | None = Field(default=None, ge=1)


class ActorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    birth_year: int | None = Field(default=None, ge=1800, le=2100)


class ActorRead(ActorBase):
    id: int
    tmdb_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ReviewBase(BaseModel):
    user_name: str | None = Field(default=None, max_length=100)
    rating: int = Field(ge=1, le=10)
    comment: str | None = None


class ReviewCreate(ReviewBase):
    movie_id: int = Field(ge=1)


class ReviewRead(ReviewBase):
    id: int
    movie_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenreDistributionItem(BaseModel):
    genre_id: int
    genre_name: str
    movie_count: int


class TopActorItem(BaseModel):
    actor_id: int
    actor_name: str
    movie_count: int


class MoviesByYearItem(BaseModel):
    release_year: int
    movie_count: int


class AverageRatingSummary(BaseModel):
    average_rating: float | None
    total_movies: int
    min_votes: int
