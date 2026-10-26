import os

# Les tests tournent toujours sur une base dédiée, jamais sur la base de développement.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://localhost/parfums_test"
)
os.environ["APP_ENV"] = "test"
