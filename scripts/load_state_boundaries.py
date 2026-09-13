import os
import tempfile
import zipfile
import logging
from pathlib import Path

import requests
import geopandas as gpd

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


# Build the Census URL in pieces
CENSUS_HOST = "https://" + "www2.census.gov"

CENSUS_STATE_URL = (
    CENSUS_HOST
    + "/geo/tiger/TIGER2024/STATE/"
    + "tl_2024_us_state.zip"
)


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Database engine
# ---------------------------------------------------------

def get_database_engine():

    url = URL.create(
        drivername="postgresql+psycopg",
        username=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=int(POSTGRES_PORT),
        database=POSTGRES_DB,
    )

    return create_engine(url)


# ---------------------------------------------------------
# Download Census data
# ---------------------------------------------------------

def download_state_boundaries(download_path):

    logger.info("Downloading Census TIGER state boundaries.")

    response = requests.get(
        CENSUS_STATE_URL,
        timeout=120
    )

    response.raise_for_status()

    with open(download_path, "wb") as file:
        file.write(response.content)

    logger.info(
        "Downloaded Census state boundary file."
    )


# ---------------------------------------------------------
# Extract shapefile
# ---------------------------------------------------------

def extract_shapefile(zip_path, extract_directory):

    with zipfile.ZipFile(zip_path, "r") as zip_file:
        zip_file.extractall(extract_directory)

    shapefiles = list(
        Path(extract_directory).glob("*.shp")
    )

    if not shapefiles:
        raise FileNotFoundError(
            "No shapefile found after extraction."
        )

    return shapefiles[0]


# ---------------------------------------------------------
# Prepare geographic data
# ---------------------------------------------------------

def prepare_state_boundaries(shapefile_path):

    logger.info("Reading Census shapefile.")

    states = gpd.read_file(shapefile_path)

    logger.info(
        "Census file contains %s geographic entities.",
        len(states)
    )

    states = states[
        [
            "STATEFP",
            "STUSPS",
            "NAME",
            "ALAND",
            "AWATER",
            "geometry"
        ]
    ].copy()

    states = states.rename(
        columns={
            "STATEFP": "state_fips",
            "STUSPS": "state_code",
            "NAME": "state_name",
            "ALAND": "land_area_m2",
            "AWATER": "water_area_m2",
        }
    )

    # Standard spatial reference for longitude/latitude
    states = states.to_crs("EPSG:4326")

    return states


# ---------------------------------------------------------
# Load into PostGIS
# ---------------------------------------------------------

def load_to_postgis(states):

    engine = get_database_engine()

    logger.info(
        "Loading state boundaries into PostGIS."
    )

    states.to_postgis(
        name="us_state_boundaries",
        con=engine,
        schema="raw",
        if_exists="replace",
        index=False,
    )

    engine.dispose()

    logger.info(
        "State boundaries successfully loaded."
    )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    with tempfile.TemporaryDirectory() as temp_directory:

        zip_path = os.path.join(
            temp_directory,
            "states.zip"
        )

        download_state_boundaries(zip_path)

        shapefile_path = extract_shapefile(
            zip_path,
            temp_directory
        )

        states = prepare_state_boundaries(
            shapefile_path
        )

        load_to_postgis(states)

    logger.info(
        "Census geographic ingestion complete."
    )


if __name__ == "__main__":
    main()