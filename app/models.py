from sqlalchemy import Column, Integer, String, Text, ForeignKey, DECIMAL, TIMESTAMP, CheckConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Genre(Base):
    __tablename__ = "genres"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    movies = relationship("MovieGenre", back_populates="genre", cascade="all, delete-orphan")


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    release_year = Column(Integer)
    runtime = Column(Integer)

    rating = Column(DECIMAL(3, 1))
    vote_count = Column(Integer)

    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        # Supports top-rated lookups, often combined with vote_count thresholding.
        Index("ix_movies_rating_vote_count", "rating", "vote_count"),
        # Supports filtering and time-based analytics rollups.
        Index("ix_movies_release_year", "release_year"),
    )

    genres = relationship("MovieGenre", back_populates="movie", cascade="all, delete-orphan")
    actors = relationship("MovieActor", back_populates="movie", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="movie", cascade="all, delete-orphan")


class Actor(Base):
    __tablename__ = "actors"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    birth_year = Column(Integer)

    movies = relationship("MovieActor", back_populates="actor")


class MovieGenre(Base):
    __tablename__ = "movie_genres"

    movie_id = Column(Integer, ForeignKey("movies.id"), primary_key=True)
    genre_id = Column(Integer, ForeignKey("genres.id"), primary_key=True)

    __table_args__ = (
        Index("ix_movie_genres_genre_id_movie_id", "genre_id", "movie_id"),
    )

    movie = relationship("Movie", back_populates="genres")
    genre = relationship("Genre", back_populates="movies")


class MovieActor(Base):
    __tablename__ = "movie_actors"

    movie_id = Column(Integer, ForeignKey("movies.id"), primary_key=True)
    actor_id = Column(Integer, ForeignKey("actors.id"), primary_key=True)

    __table_args__ = (
        # PK covers (movie_id, actor_id). This index helps reverse lookups by actor.
        Index("ix_movie_actors_actor_id", "actor_id"),
    )

    movie = relationship("Movie", back_populates="actors")
    actor = relationship("Actor", back_populates="movies")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), index=True)

    user_name = Column(String(100))
    rating = Column(Integer)
    comment = Column(Text)

    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 10", name="rating_range"),
    )

    movie = relationship("Movie", back_populates="reviews")