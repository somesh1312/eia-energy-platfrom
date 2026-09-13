with source as (

    select *
    from {{ source('raw', 'eia_seds') }}

),

cleaned as (

    select

        cast(period as integer) as year,

        trim(series_id) as series_id,

        trim(series_description) as series_description,

        trim(state_id) as state_id,

        trim(state_description) as state_description,

        case

            when value is null then null

            when trim(value) = '' then null

            else cast(value as numeric)

        end as value,

        trim(unit) as unit,

        loaded_at

    from source

)

select *
from cleaned