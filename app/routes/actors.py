from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Actor
from app.schemas import ActorCreate, ActorRead, ActorUpdate


router = APIRouter(prefix="/actors", tags=["actors"])

DEFAULT_LIMIT = 100
MAX_LIMIT = 200


@router.post("", response_model=ActorRead, status_code=status.HTTP_201_CREATED)
def create_actor(payload: ActorCreate, db: Session = Depends(get_db)) -> Actor:
    actor = Actor(**payload.model_dump())
    db.add(actor)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Actor already exists.") from exc

    db.refresh(actor)
    return actor


@router.get("", response_model=list[ActorRead])
def get_actors(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    db: Session = Depends(get_db),
) -> list[Actor]:
    return db.query(Actor).order_by(Actor.id).offset(skip).limit(limit).all()


@router.put("/{actor_id}", response_model=ActorRead)
def update_actor(actor_id: int, payload: ActorUpdate, db: Session = Depends(get_db)) -> Actor:
    actor = db.query(Actor).filter(Actor.id == actor_id).first()
    if actor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actor not found.")

    for field_name, field_value in payload.model_dump(exclude_unset=True).items():
        setattr(actor, field_name, field_value)

    db.commit()
    db.refresh(actor)
    return actor
