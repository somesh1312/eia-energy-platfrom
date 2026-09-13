U.S. Energy Data Platform

A production-inspired ELT and geospatial analytics project that ingests U.S. state-level energy data from the U.S. Energy Information Administration (EIA), loads it into PostgreSQL/PostGIS, models it with dbt, enriches it with U.S. Census TIGER/Line boundaries, and produces spatial energy analytics.

I built this project as hands-on practice with energy-domain data, API ingestion, PostgreSQL/PostGIS, dimensional modeling, dbt, data quality, and geospatial analytics.

Project Highlights

Ingests 518,872 annual EIA SEDS observations covering 2014–2024

Handles 962 distinct energy series

Uses API pagination to load data in 5,000-row batches

Preserves source data in a dedicated raw layer

Models the warehouse with dim_state, dim_energy_series, and fact_state_energy

Enriches EIA state records with Census TIGER/Line geometry in PostGIS

Uses dbt tests for uniqueness, nullability, and dimensional relationships

Produces state-level analytics for energy production intensity and production-consumption balance

Key Findings

2024 Primary Energy Production Intensity

Texas had the highest absolute total primary energy production in 2024, but West Virginia ranked highest after normalizing production by land area.

Top states by production intensity:

West Virginia

Pennsylvania

Texas

Louisiana

Ohio



2024 Production vs. Consumption

The project compares:

TEPRB — Total primary energy production

TETCB — Total energy consumption

Both are measured in Billion Btu, allowing a direct production-consumption comparison.

For each geography:

energy_balance = production - consumption

In 2024:

12 mapped geographies were net producers

39 were net consumers

Texas had the largest positive production-consumption balance

California had the largest negative balance

New Mexico produced about 12.46× its total energy consumption

The production-consumption balance is an analytical indicator and should not be interpreted directly as physical interstate energy exports or imports.

Architecture

flowchart LR
    A[EIA SEDS API] --> B[Python API Ingestion]
    C[Census TIGER/Line] --> D[GeoPandas Loader]

    B --> E[(PostgreSQL / PostGIS)]
    D --> E

    E --> F[raw.eia_seds]
    E --> G[raw.us_state_boundaries]

    F --> H[dbt Staging]
    G --> H

    H --> I[dim_state]
    H --> J[dim_energy_series]
    H --> K[fact_state_energy]

    I --> L[Analytics Marts]
    J --> L
    K --> L

    L --> M[PostGIS Spatial Analysis]
    M --> N[GeoPandas Visualization]

Data Sources

EIA State Energy Data System (SEDS)

Annual state-level energy production, consumption, prices, expenditures, emissions, and related energy measures.

Period used: 2014–2024

Observations loaded: 518,872

Energy series: 962

EIA geographic identifiers: 54

Source: https://www.eia.gov/state/seds/

U.S. Census TIGER/Line

Official state boundary geometry is used to spatially enrich valid EIA state-level records.

Source: https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html

Geographic Modeling

EIA contains 54 geographic identifiers, but not every identifier represents a physical U.S. state boundary.

Three EIA entities do not directly map to Census state polygons:

EIA ID

Description

Spatially Mappable

US

United States

No

X3

Federal Offshore - Gulf of America

No

X5

Federal Offshore - Pacific

No

These records are not discarded. They remain available in the raw and warehouse layers, while spatial models explicitly filter to geographies that have valid Census geometry.

This preserves source fidelity without forcing invalid geographic relationships.

Data Model

erDiagram
    DIM_STATE ||--o{ FACT_STATE_ENERGY : state_key
    DIM_ENERGY_SERIES ||--o{ FACT_STATE_ENERGY : series_key

    DIM_STATE {
        string state_key
        string state_id
        string state_name
        string state_fips
        numeric land_area_m2
        numeric water_area_m2
        geometry geometry
        boolean is_mappable
    }

    DIM_ENERGY_SERIES {
        string series_key
        string series_id
        string series_description
        string unit
    }

    FACT_STATE_ENERGY {
        string energy_fact_key
        string state_key
        string series_key
        int year
        numeric value
        timestamp loaded_at
    }

Core Models

dim_state — EIA geography dimension enriched with Census state geometry

dim_energy_series — energy series metadata and measurement units

fact_state_energy — annual energy observations by geography and series

mart_state_energy_production — total primary energy production and production intensity

mart_state_energy_balance — annual production vs. consumption comparison

Engineering Decisions

Raw Data Preservation

The raw layer stores source values with minimal transformation so the original provider data remains recoverable.

Type casting, standardization, and business logic are handled downstream in dbt.

ELT Architecture

The project follows an Extract → Load → Transform pattern:

API / Census
    ↓
Python loaders
    ↓
PostgreSQL / PostGIS raw layer
    ↓
dbt transformations
    ↓
Analytics marts

This keeps ingestion separate from analytical modeling.

API Pagination

The EIA API returns data in limited pages. The Python ingestion process retrieves the dataset in 5,000-row batches and loads each page into PostgreSQL before requesting the next page.

This avoids requiring the full dataset to remain in memory during ingestion.

Full-Refresh Strategy

At roughly 519K records, a full refresh is simple and reproducible for this project.

If data volume or refresh frequency increased, the next design step would be an incremental strategy with source-key validation, change detection, and upsert logic.

Dimensional Modeling

The source includes hundreds of metrics with different units, including:

Billion Btu

Thousand barrels

Million dollars

Dollars per million Btu

Million metric tons CO2

Values with different units cannot be meaningfully aggregated together.

Separating dim_energy_series from fact_state_energy preserves the relationship between every measurement and its definition/unit while keeping the fact table compact.

Geospatial Enrichment

Census state polygons are stored as native PostGIS geometry objects rather than coordinates embedded in application code.

This allows spatial operations to execute directly in PostgreSQL, including:

ST_Centroid

ST_GeometryType

ST_SRID

GeoPandas is used as the presentation layer for map generation.

Data Quality

dbt tests validate:

primary/surrogate key uniqueness

required fields

dimension-to-fact relationships

nullability of analytics fields

spatial geometry availability for mapped analytical records

The raw-to-staging transformation also preserves source row counts so data is not silently lost during standardization.

Repository Structure

eia-energy-platform/
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── requirements.txt
│
├── scripts/
│   ├── ingest_eia.py
│   ├── load_state_boundaries.py
│   └── create_energy_map.py
│
├── notebooks/
│   └── 01_explore_eia.ipynb
│
├── dbt_energy/
│   ├── dbt_project.yml
│   ├── profiles.yml.example
│   ├── macros/
│   │   └── generate_schema_name.sql
│   └── models/
│       ├── staging/
│       │   ├── sources.yml
│       │   ├── stg_eia_seds.sql
│       │   └── stg_state_boundaries.sql
│       └── marts/
│           ├── dim_state.sql
│           ├── dim_energy_series.sql
│           ├── fact_state_energy.sql
│           ├── mart_state_energy_production.sql
│           ├── mart_state_energy_balance.sql
│           └── schema.yml
│
└── outputs/
    └── energy_production_intensity_2024.png

Running Locally

1. Clone the repository

git clone https://github.com/<your-username>/eia-energy-platform.git
cd eia-energy-platform

2. Create a Python environment

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

3. Configure environment variables

cp .env.example .env

Add your EIA API key and local PostgreSQL credentials to .env.

Never commit .env.

4. Start PostgreSQL/PostGIS

docker compose up -d

Verify the container:

docker compose ps

5. Load EIA SEDS data

python scripts/ingest_eia.py

6. Load Census state boundaries

python scripts/load_state_boundaries.py

7. Run dbt

set -a
source .env
set +a

cd dbt_energy
dbt build --profiles-dir .
cd ..

8. Generate the map

python scripts/create_energy_map.py

The output is written to:

outputs/energy_production_intensity_2024.png

Example Analytical Questions

This modeled dataset can answer questions such as:

Which states produce the most primary energy?

Which states have the highest production per square kilometer?

Which states produce more energy than they consume?

How has state-level production-consumption balance changed since 2014?

How do energy production patterns differ geographically across the United States?

Limitations

The project currently uses a full-refresh ingestion strategy.

State-level production minus consumption should not be treated as a direct measure of interstate energy flows.

Spatial analytics are limited to EIA entities that map reliably to Census state boundaries.

The project runs locally and does not currently include workflow orchestration or cloud deployment.

Potential Next Steps

Add incremental ingestion

Add CI checks for dbt models and Python quality

Schedule ingestion with an orchestration tool

Add renewable-energy and CO2 analytics marts

Deploy PostgreSQL/dbt workloads to a cloud environment

Add an interactive geospatial dashboard

Why I Built This

I wanted a project that went beyond loading a CSV into a dataframe.

The goal was to practice how a data engineer handles:

a real public API

pagination

source preservation

mixed measurement units

multiple authoritative data sources

dimensional modeling

data quality validation

imperfect geography mappings

native spatial data

business-facing analytical outputs

The result is a small but reproducible energy data platform that connects data ingestion, warehouse modeling, geospatial engineering, and analytics in one workflow.