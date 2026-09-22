import os

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, Query

load_dotenv()

app = FastAPI(
    title="Energy Infrastructure Site Intelligence API",
    version="1.0.0",
)


def get_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


@app.get("/plants/nearby")
def nearby_plants(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(50, gt=0, le=500),
):
    sql = """
        SELECT
            plant_code,
            plant_name,
            state,
            ROUND(
                (
                    ST_Distance(
                        geometry::geography,
                        ST_SetSRID(
                            ST_MakePoint(%s, %s),
                            4326
                        )::geography
                    ) / 1000
                )::numeric,
                2
            ) AS distance_km
        FROM analytics.dim_power_plant
        WHERE geometry IS NOT NULL
          AND ST_DWithin(
                geometry::geography,
                ST_SetSRID(
                    ST_MakePoint(%s, %s),
                    4326
                )::geography,
                %s
          )
        ORDER BY distance_km;
    """

    radius_m = radius_km * 1000

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    lon,
                    lat,
                    lon,
                    lat,
                    radius_m,
                ),
            )

            rows = cur.fetchall()

    plants = [
        {
            "plant_code": row[0],
            "plant_name": row[1],
            "state": row[2],
            "distance_km": float(row[3]),
        }
        for row in rows
    ]

    return {
        "center": {
            "latitude": lat,
            "longitude": lon,
        },
        "radius_km": radius_km,
        "plant_count": len(plants),
        "plants": plants,
    }