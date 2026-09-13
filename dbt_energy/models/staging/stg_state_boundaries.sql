select

    trim(state_fips) as state_fips,

    trim(state_code) as state_code,

    trim(state_name) as state_name,

    land_area_m2,

    water_area_m2,

    geometry

from {{ source('raw', 'us_state_boundaries') }}