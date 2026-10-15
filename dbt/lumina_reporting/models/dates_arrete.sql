-- Les "dates d'arrêté" : les jours où l'on prend une photo du portefeuille.
-- = le dernier jour de chaque mois écoulé + aujourd'hui.

with fins_de_mois as (
    select (date_trunc('month', m) + interval '1 month - 1 day')::date as date_arrete
    from generate_series(
        (select date_trunc('month', min(date_decaissement)) from {{ source('entrepot', 'fact_prets') }}),
        current_date,
        interval '1 month'
    ) as m
),

arretes as (
    select date_arrete, false as est_dernier_arrete
    from fins_de_mois
    where date_arrete < current_date
    union all
    select current_date, true
)

select
    date_arrete,
    est_dernier_arrete,
    to_char(date_arrete, 'YYYY-MM')                                    as mois,
    lag(date_arrete) over (order by date_arrete)                       as date_arrete_precedente,
    extract(month from date_arrete) in (3, 6, 9, 12) or est_dernier_arrete as est_fin_trimestre
from arretes
