from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set.")
    return database_url


def get_db_connection():
    return psycopg.connect(get_database_url())