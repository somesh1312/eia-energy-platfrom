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

consumption as (

    select

        f.year,
        f.state_key,
        f.value as consumption_billion_btu

    from {{ ref('fact_state_energy') }} f

    inner join {{ ref('dim_energy_series') }} s
        on f.series_key = s.series_key

    where s.series_id = 'TETCB'

),

states as (

    select

        state_key,
        state_id,
        state_name,
        geometry,
        is_mappable

    from {{ ref('dim_state') }}

),

combined as (

    select

        p.year,

        p.state_key,

        p.production_billion_btu,

        c.consumption_billion_btu

    from production p

    inner join consumption c

        on p.year = c.year
        and p.state_key = c.state_key

),

final as (

    select

        c.year,

        s.state_id,

        s.state_name,

        c.production_billion_btu,

        c.consumption_billion_btu,

        c.production_billion_btu
        - c.consumption_billion_btu
            as energy_balance_billion_btu,

        c.production_billion_btu
        /
        nullif(c.consumption_billion_btu, 0)
            as production_consumption_ratio,

        case

            when c.production_billion_btu
                 > c.consumption_billion_btu
                then 'Net Producer'

            when c.production_billion_btu
                 < c.consumption_billion_btu
                then 'Net Consumer'

            else 'Balanced'

        end as energy_balance_category,

        s.geometry

    from combined c

    inner join states s
        on c.state_key = s.state_key

    where s.is_mappable = true

)

select *
from final