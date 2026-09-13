with series as (

    select distinct

        series_id,
        series_description,
        unit

    from {{ ref('stg_eia_seds') }}

),

final as (

    select

        md5('series|' || series_id) as series_key,

        series_id,

        series_description,

        unit

    from series

)

select *
from final