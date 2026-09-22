{{ config(
    materialized='table'
) }}

with plants as (

    select *
    from {{ ref('stg_eia860_plants') }}

),

final as (

    select

        plant_snapshot_key,
        report_year,
        plant_code,
        plant_name,
        utility_id,
        utility_name,
        city,
        state,
        county,
        latitude,
        longitude,
        is_spatially_mappable,

        case
            when is_spatially_mappable then
                ST_SetSRID(
                    ST_MakePoint(longitude, latitude),
                    4326
                )::geometry(Point, 4326)
            else null
        end as geometry,

        loaded_at

    from plants

)

select *
from final