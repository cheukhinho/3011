from fastapi import FastAPI
from app.database import engine, ensure_analytics_indexes, ensure_schema_extensions
from app import models
from app.routes import actors, analytics, movies, recommendations, reviews

models.Base.metadata.create_all(bind=engine)
ensure_schema_extensions()
ensure_analytics_indexes()

app = FastAPI()

app.include_router(movies.router)
app.include_router(actors.router)
app.include_router(reviews.router)
app.include_router(analytics.router)
app.include_router(recommendations.router)