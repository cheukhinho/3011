# 3011


## Dataset

This project uses the TMDB 5000 Movies dataset from Kaggle.

Source:
https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata

The dataset is used to populate the database and support analytics
endpoints such as top-rated movies and genre distribution.

## Database

Set DATABASE_URL to your PostgreSQL connection string before running the app or importer.

SQLite is only intended for local smoke tests and test runs when ALLOW_SQLITE_URLS=1 is set.