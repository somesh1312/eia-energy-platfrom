with eia_states as (

    select distinct

        state_id,
        state_description

    from {{ ref('stg_eia_seds') }}

),

state_boundaries as (

    select

        state_code,
        state_name,
        state_fips,
        land_area_m2,
        water_area_m2,
        geometry

    from {{ ref('stg_state_boundaries') }}

),

final as (

    select

        md5('state|' || e.state_id) as state_key,

        e.state_id,

        e.state_description as state_name,

        b.state_fips,

        b.land_area_m2,

        b.water_area_m2,

        b.geometry,

        case
            when b.geometry is not null then true
            else false
        end as is_mappable

    from eia_states e

    left join state_boundaries b
        on e.state_id = b.state_code

)

select *
from final