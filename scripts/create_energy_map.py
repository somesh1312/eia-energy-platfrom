import os
import logging

import geopandas as gpd
import matplotlib.pyplot as plt

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


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------

def get_engine():

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
# Read spatial analytics mart
# ---------------------------------------------------------

def get_energy_data(engine):

    query = """
    SELECT
        state_id,
        state_name,
        production_billion_btu,
        land_area_sq_km,
        production_billion_btu_per_sq_km,
        geometry
    FROM analytics.mart_state_energy_production
    WHERE year = 2024
      AND state_id NOT IN ('AK', 'HI', 'DC')
    """

    return gpd.read_postgis(
        query,
        con=engine,
        geom_col="geometry"
    )


# ---------------------------------------------------------
# Create map
# ---------------------------------------------------------

def create_map(gdf):

    fig, ax = plt.subplots(figsize=(15, 9))

    gdf.plot(
        column="production_billion_btu_per_sq_km",
        legend=True,
        ax=ax,
        edgecolor="black",
        linewidth=0.4,
        legend_kwds={
            "label": "Billion Btu per square kilometer",
            "shrink": 0.7
        }
    )

    ax.set_title(
        "U.S. Primary Energy Production Intensity — 2024",
        fontsize=18,
        pad=20
    )

    ax.set_axis_off()

    plt.tight_layout()

    output_path = "outputs/energy_production_intensity_2024.png"

    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )

    logger.info(
        "Map saved to %s",
        output_path
    )

    plt.show()


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    engine = get_engine()

    logger.info(
        "Reading energy production data from PostGIS."
    )

    gdf = get_energy_data(engine)

    logger.info(
        "Loaded %s geographic records.",
        len(gdf)
    )

    create_map(gdf)

    engine.dispose()


if __name__ == "__main__":
    main()