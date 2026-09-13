with energy as (

    select

        year,
        state_id,
        series_id,
        value,
        loaded_at

    from {{ ref('stg_eia_seds') }}

),

final as (

    select

        md5(
            year::text
            || '|'
            || state_id
            || '|'
            || series_id
        ) as energy_fact_key,

        md5('state|' || state_id) as state_key,

        md5('series|' || series_id) as series_key,

        year,

        value,

        loaded_at

    from energy

)

select *
from final