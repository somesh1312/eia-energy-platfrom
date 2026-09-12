import os
import time
import logging
from datetime import datetime, timezone

import requests
import psycopg
from dotenv import load_dotenv


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

load_dotenv()

EIA_API_KEY = os.getenv("EIA_API_KEY")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

EIA_URL = "https://api.eia.gov/v2/seds/data/"

PAGE_SIZE = 5000


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

def validate_environment():
    required_variables = {
        "EIA_API_KEY": EIA_API_KEY,
        "POSTGRES_DB": POSTGRES_DB,
        "POSTGRES_USER": POSTGRES_USER,
        "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
    }

    missing = [
        name
        for name, value in required_variables.items()
        if not value
    ]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {missing}"
        )


# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------

def get_database_connection():
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


# ---------------------------------------------------------
# Create raw table
# ---------------------------------------------------------

def create_raw_table(conn):

    sql = """
    CREATE TABLE IF NOT EXISTS raw.eia_seds (
        period TEXT,
        series_id TEXT,
        series_description TEXT,
        state_id TEXT,
        state_description TEXT,
        value TEXT,
        unit TEXT,
        loaded_at TIMESTAMPTZ NOT NULL
    );
    """

    with conn.cursor() as cur:
        cur.execute(sql)

    conn.commit()

    logger.info("raw.eia_seds table is ready.")


# ---------------------------------------------------------
# Full-refresh preparation
# ---------------------------------------------------------

def truncate_raw_table(conn):

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE raw.eia_seds;")

    conn.commit()

    logger.info("Existing raw EIA records removed.")


# ---------------------------------------------------------
# Request one API page
# ---------------------------------------------------------

def fetch_eia_page(offset):

    params = {
        "api_key": EIA_API_KEY,
        "frequency": "annual",
        "data[0]": "value",
        "start": "2014",
        "end": "2024",
        "sort[0][column]": "stateId",
        "sort[0][direction]": "desc",
        "offset": offset,
        "length": PAGE_SIZE,
    }

    response = requests.get(
        EIA_URL,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    result = response.json()["response"]

    return result


# ---------------------------------------------------------
# Load page into PostgreSQL
# ---------------------------------------------------------

def load_page(conn, rows, loaded_at):

    insert_sql = """
    INSERT INTO raw.eia_seds (
        period,
        series_id,
        series_description,
        state_id,
        state_description,
        value,
        unit,
        loaded_at
    )
    VALUES (
        %s, %s, %s, %s,
        %s, %s, %s, %s
    );
    """

    records = []

    for row in rows:

        records.append(
            (
                row.get("period"),
                row.get("seriesId"),
                row.get("seriesDescription"),
                row.get("stateId"),
                row.get("stateDescription"),
                row.get("value"),
                row.get("unit"),
                loaded_at,
            )
        )

    with conn.cursor() as cur:
        cur.executemany(insert_sql, records)

    conn.commit()


# ---------------------------------------------------------
# Main ingestion process
# ---------------------------------------------------------

def ingest():

    validate_environment()

    logger.info("Starting EIA SEDS ingestion.")

    loaded_at = datetime.now(timezone.utc)

    with get_database_connection() as conn:

        create_raw_table(conn)

        truncate_raw_table(conn)

        offset = 0
        total_loaded = 0
        total_available = None

        while True:

            logger.info(
                "Requesting EIA records starting at offset %s",
                offset
            )

            result = fetch_eia_page(offset)

            rows = result["data"]

            if total_available is None:
                total_available = int(result["total"])

                logger.info(
                    "EIA reports %s total records.",
                    total_available
                )

            if not rows:
                break

            load_page(
                conn=conn,
                rows=rows,
                loaded_at=loaded_at
            )

            total_loaded += len(rows)

            logger.info(
                "Loaded %s / %s records.",
                total_loaded,
                total_available
            )

            if total_loaded >= total_available:
                break

            offset += PAGE_SIZE

            # Small pause so we're polite to the public API
            time.sleep(0.1)

    logger.info(
        "Ingestion complete. %s records loaded.",
        total_loaded
    )


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    ingest()