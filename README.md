# Energy Infrastructure Site Intelligence Platform

A small geospatial data platform built with public U.S. energy and geographic datasets to explore energy infrastructure, data quality, and location-based analysis.

The project combines **EIA SEDS**, **EIA-860 power plant data**, and **U.S. Census TIGER/Line boundaries** using Python, PostgreSQL/PostGIS, dbt, and FastAPI.

The platform supports state-level energy analysis and location-based queries such as:

> What power infrastructure exists within 50 km of a candidate location?

---

## Architecture

```text
EIA SEDS ──────────┐
                   │
EIA-860 ───────────┼──► Python Ingestion
                   │          │
Census TIGER ──────┘          ▼
                         PostgreSQL
                         raw schema
                              │
                              ▼
                             dbt
                     staging + validation
                              │
                              ▼
                       PostgreSQL/PostGIS
                       ├── State polygons
                       └── Power plant points
                              │
                              ▼
                        Spatial queries
                              │
                              ▼
                           FastAPI
                              │
                              ▼
                       /plants/nearby
```

---

## Example

The API can search for power plants around a candidate location.

```http
GET /plants/nearby?lat=27.8&lon=-97.4&radius_km=50
```

Example response:

```json
{
  "center": {
    "latitude": 27.8,
    "longitude": -97.4
  },
  "radius_km": 50,
  "plant_count": 29,
  "plants": [
    {
      "plant_code": "3441",
      "plant_name": "Nueces Bay",
      "state": "TX",
      "distance_km": 2.86
    },
    {
      "plant_code": "55206",
      "plant_name": "Corpus Christi Energy Center",
      "state": "TX",
      "distance_km": 3.19
    }
  ]
}
```

---

## Data Pipeline

### 1. Ingestion

Python ingestion pipelines load public energy and geographic datasets into PostgreSQL.

The EIA-860 loader:

- validates the incoming source structure
- preserves annual plant snapshots
- uses `(report_year, plant_code)` as the record grain
- supports idempotent reruns through UPSERT behavior
- preserves source coordinate values before transformation

### 2. Transformation and Quality

dbt separates source ingestion from analytical transformation.

The staging layer handles:

- type conversion
- coordinate parsing
- latitude/longitude range validation
- deterministic snapshot keys
- spatial eligibility
- uniqueness and nullability tests

The EIA-860 2024 source contains **16,132 plant records**.

- **16,104** have usable coordinates
- **28** are retained as valid plant records without spatial geometry

Records are not discarded solely because geographic coordinates are unavailable.

### 3. Spatial Modeling

Valid plant coordinates are converted into PostGIS geometry:

```sql
ST_SetSRID(
    ST_MakePoint(longitude, latitude),
    4326
)
```

Plant locations are stored as `Point` geometries using **EPSG:4326**, while Census TIGER boundaries provide state `Polygon` and `MultiPolygon` geometries.

This supports:

- point-in-polygon validation
- plant-to-state spatial relationships
- radius searches
- proximity analysis

### 4. Spatial Data Quality

Plant coordinates were independently compared with Census state boundaries.

For the 16,104 spatially mappable plants:

- 16,064 matched their reported state
- 27 produced a different state through the spatial relationship
- 13 did not match a state polygon

These records are preserved as data-quality signals rather than automatically overwritten.

---

## Spatial Query Performance

The nearby-infrastructure query uses `ST_DWithin` with PostGIS `geography` so search radii can be expressed in meters.

An initial execution plan showed a sequential scan because the existing GiST index covered `geometry`, while the query operated on:

```sql
geometry::geography
```

A GiST expression index was added for the actual query pattern:

```sql
CREATE INDEX idx_dim_power_plant_geography
ON analytics.dim_power_plant
USING GIST ((geometry::geography))
WHERE geometry IS NOT NULL;
```

In a local test using a 50 km search:

| | Initial Query | Indexed Query |
|---|---:|---:|
| Access pattern | Sequential scan | Bitmap index scan |
| Plant rows considered | ~16,000 | 33 candidates |
| Matching plants | 29 | 29 |
| Execution time | ~380 ms | ~60 ms |

These measurements are from the local development environment and are intended to demonstrate query-plan analysis rather than large-scale performance benchmarking.

---

## Data Model

```text
raw
├── eia_seds
├── eia860_plants
└── us_state_boundaries

staging
├── stg_eia_seds
├── stg_eia860_plants
└── stg_state_boundaries

analytics
├── dim_state
├── dim_energy_series
├── dim_power_plant
├── fact_state_energy
├── mart_state_energy_production
└── mart_state_energy_balance
```

---

## Technology

- **Python** — ingestion and API
- **PostgreSQL** — persistent analytical storage
- **PostGIS** — spatial modeling and queries
- **dbt** — transformation and data-quality testing
- **FastAPI** — location-based API
- **Docker** — local PostgreSQL/PostGIS environment
- **Pandas / GeoPandas** — source processing
- **U.S. EIA** — energy datasets
- **U.S. Census TIGER/Line** — geographic boundaries

---

## Running Locally

### Start PostgreSQL/PostGIS

```bash
docker compose up -d
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run EIA-860 ingestion

```bash
python scripts/ingest_eia860_plants.py
```

### Build dbt models

```bash
cd dbt_energy
dbt build
cd ..
```

### Start the API

```bash
uvicorn api.main:app --reload
```

FastAPI documentation is then available at:

```text
http://127.0.0.1:8000/docs
```

---

## Key Engineering Decisions

**Preserve raw source data.**  
Source values are retained before business interpretation so transformations remain reproducible.

**Separate ingestion from transformation.**  
Python handles source acquisition and loading, while dbt owns analytical modeling and validation.

**Preserve non-spatial records.**  
Missing coordinates do not make an otherwise valid plant record unusable for every analytical purpose.

**Model annual snapshots explicitly.**  
`report_year + plant_code` allows future EIA-860 reporting years to coexist without overwriting previous snapshots.

**Measure performance rather than assuming it.**  
Spatial indexes were evaluated using PostgreSQL execution plans, and the index was aligned with the actual query expression.

---

## Future Work

Potential extensions include:

- incremental ingestion across additional EIA-860 reporting years
- investigation and classification of spatial state mismatches
- additional infrastructure layers
- API pagination and filtering
- production observability and pipeline monitoring

The current implementation intentionally focuses on data ingestion, data quality, spatial modeling, and proximity queries rather than adding infrastructure that is not required by the workload.
