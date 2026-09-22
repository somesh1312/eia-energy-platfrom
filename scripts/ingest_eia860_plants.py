import os
import logging
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import psycopg
from dotenv import load_dotenv


load_dotenv()


POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


EIA860_ZIP_PATH = Path("data/raw/eia8602024.zip")
PLANT_FILE = "2___Plant_Y2024.xlsx"
PLANT_SHEET = "Plant"
REPORT_YEAR = 2024


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

def get_database_connection():
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )

def read_source():
    logger.info("Reading EIA-860 plant workbook.")

    with ZipFile(EIA860_ZIP_PATH) as archive:
        workbook = BytesIO(
            archive.read(PLANT_FILE)
        )

        df = pd.read_excel(
            workbook,
            sheet_name=PLANT_SHEET,
            header=1,
            dtype=object,
            keep_default_na=False,
        )

    logger.info(
        "Read %s plant records.",
        len(df)
    )

    return df

REQUIRED_COLUMNS = [
    "Utility ID",
    "Utility Name",
    "Plant Code",
    "Plant Name",
    "City",
    "State",
    "County",
    "Latitude",
    "Longitude",
]


def validate_source(df):
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required source columns: {missing_columns}"
        )

    if df["Plant Code"].eq("").any():
        raise ValueError("Plant Code contains blank values.")

    duplicate_count = df["Plant Code"].duplicated().sum()

    if duplicate_count:
        raise ValueError(
            f"Found {duplicate_count} duplicate Plant Codes."
        )

    logger.info(
        "Source validation passed: %s records, unique Plant Codes.",
        len(df),
    )

def create_raw_table(conn):
    sql = """
    CREATE SCHEMA IF NOT EXISTS raw;

    CREATE TABLE IF NOT EXISTS raw.eia860_plants (
        report_year INTEGER NOT NULL,
        plant_code TEXT NOT NULL,
        plant_name TEXT,
        utility_id TEXT,
        utility_name TEXT,
        city TEXT,
        state TEXT,
        county TEXT,
        latitude_raw TEXT,
        longitude_raw TEXT,
        loaded_at TIMESTAMPTZ NOT NULL,

        PRIMARY KEY (report_year, plant_code)
    );
    """

    with conn.cursor() as cur:
        cur.execute(sql)

    conn.commit()

    logger.info("raw.eia860_plants table is ready.")

def load_raw_plants(conn, df, loaded_at):
    sql = """
    INSERT INTO raw.eia860_plants (
        report_year,
        plant_code,
        plant_name,
        utility_id,
        utility_name,
        city,
        state,
        county,
        latitude_raw,
        longitude_raw,
        loaded_at
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s
    )
    ON CONFLICT (report_year, plant_code)
    DO UPDATE SET
        plant_name = EXCLUDED.plant_name,
        utility_id = EXCLUDED.utility_id,
        utility_name = EXCLUDED.utility_name,
        city = EXCLUDED.city,
        state = EXCLUDED.state,
        county = EXCLUDED.county,
        latitude_raw = EXCLUDED.latitude_raw,
        longitude_raw = EXCLUDED.longitude_raw,
        loaded_at = EXCLUDED.loaded_at;
    """

    records = []

    for _, row in df.iterrows():
        records.append(
            (
                REPORT_YEAR,
                str(row["Plant Code"]).strip(),
                str(row["Plant Name"]),
                str(row["Utility ID"]).strip(),
                str(row["Utility Name"]),
                str(row["City"]),
                str(row["State"]).strip(),
                str(row["County"]),
                str(row["Latitude"]),
                str(row["Longitude"]),
                loaded_at,
            )
        )

    with conn.cursor() as cur:
        cur.executemany(sql, records)

    conn.commit()

    logger.info(
        "Upserted %s EIA-860 plant records.",
        len(records),
    )

def ingest():
    loaded_at = datetime.now(timezone.utc)

    df = read_source()

    validate_source(df)

    with get_database_connection() as conn:
        create_raw_table(conn)
        load_raw_plants(
            conn=conn,
            df=df,
            loaded_at=loaded_at,
        )

    logger.info("EIA-860 plant ingestion complete.")


if __name__ == "__main__":
    ingest()