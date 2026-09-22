with source as (

    select *
    from {{ source('raw', 'eia860_plants') }}

),

typed as (

    select

        report_year,

        trim(plant_code) as plant_code,

        trim(plant_name) as plant_name,

        nullif(trim(utility_id), '') as utility_id,

        nullif(trim(utility_name), '') as utility_name,

        nullif(trim(city), '') as city,

        nullif(trim(state), '') as state,

        nullif(trim(county), '') as county,

        case
            when nullif(trim(latitude_raw), '') is null
                then null

            when trim(latitude_raw)
                ~ '^-?[0-9]+(\.[0-9]+)?$'
                then trim(latitude_raw)::double precision

            else null
        end as latitude,

        case
            when nullif(trim(longitude_raw), '') is null
                then null

            when trim(longitude_raw)
                ~ '^-?[0-9]+(\.[0-9]+)?$'
                then trim(longitude_raw)::double precision

            else null
        end as longitude,

        loaded_at

    from source

),

validated as (

    select

        md5(
            report_year::text
            || '|'
            || plant_code
        ) as plant_snapshot_key,

        *,

        case
            when latitude between -90 and 90
             and longitude between -180 and 180
                then true
            else false
        end as is_spatially_mappable

    from typed

)

select *
from validated