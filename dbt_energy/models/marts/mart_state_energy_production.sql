with production as (

    select

        f.year,
        f.state_key,
        f.value as production_billion_btu

    from {{ ref('fact_state_energy') }} f

    inner join {{ ref('dim_energy_series') }} s
        on f.series_key = s.series_key

    where s.series_id = 'TEPRB'

),

states as (

    select

        state_key,
        state_id,
        state_name,
        state_fips,
        land_area_m2,
        geometry,
        is_mappable

    from {{ ref('dim_state') }}

),

final as (

    select

        p.year,

        s.state_id,
        s.state_name,
        s.state_fips,

        p.production_billion_btu,

        s.land_area_m2,

        s.land_area_m2 / 1000000.0
            as land_area_sq_km,

        p.production_billion_btu
        /
        nullif(
            s.land_area_m2 / 1000000.0,
            0
        )
            as production_billion_btu_per_sq_km,

        s.geometry

    from production p

    inner join states s
        on p.state_key = s.state_key

    where s.is_mappable = true

)

select *
from final