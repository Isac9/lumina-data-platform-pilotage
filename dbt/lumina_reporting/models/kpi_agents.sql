-- Performance des agents commerciaux : ce qu'ils ont vendu ET la qualité
-- de leur portefeuille aujourd'hui (un bon agent vend à des clients qui paient).
{{ config(post_hook="{{ appliquer_rls() }}") }}

with ventes as (
    select id_agent, count(*) as nb_ventes, sum(montant_finance) as montant_finance
    from {{ source('entrepot', 'fact_prets') }}
    group by id_agent
),

portefeuille as (
    select
        id_agent,
        count(*)                                                    as nb_prets_actifs,
        sum(encours)                                                as encours,
        coalesce(sum(encours) filter (where jours_retard > 30), 0)  as encours_par30
    from {{ ref('fct_situation_prets') }}
    where est_dernier_arrete
    group by id_agent
)

select
    a.id_agent,
    a.code_entite,
    a.nom_complet                                                  as nom_agent,
    a.zone,
    coalesce(v.nb_ventes, 0)                                       as nb_ventes,
    coalesce(v.montant_finance, 0)                                 as montant_finance,
    coalesce(p.nb_prets_actifs, 0)                                 as nb_prets_actifs,
    coalesce(p.encours, 0)                                         as encours,
    coalesce(p.encours_par30, 0)                                   as encours_par30,
    round(coalesce(p.encours_par30, 0) / nullif(p.encours, 0), 4)  as par30
from {{ source('entrepot', 'dim_agent') }} a
left join ventes v using (id_agent)
left join portefeuille p using (id_agent)
